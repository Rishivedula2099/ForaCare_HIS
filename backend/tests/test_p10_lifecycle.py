"""P10-B02: platform Super Admin -> organisation -> facilities -> Hospital Admin -> staff.

Covers the permission boundaries between the levels, tenant and facility
activation / suspension / safe deactivation, and that facility context is derived
and validated server-side rather than trusted from the client.
"""
import asyncio
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from tests.test_p10_platform_setup import _payload

DEMO = "Demo@123"
STRONG = "Str0ng!Passw0rd#9"


# ------------------------------------------------------------------- helpers


def _run(coro_factory):
    async def runner():
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        try:
            async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as db:
                return await coro_factory(db)
        finally:
            await engine.dispose()

    return asyncio.run(runner())


async def _purge_tenants(db, codes):
    for code in codes:
        row = (await db.execute(text("SELECT id FROM tenants WHERE code = :c"), {"c": code})).first()
        if row is None:
            continue
        p = {"t": row[0]}
        for sql in (
            "UPDATE facilities SET status_changed_by = NULL WHERE tenant_id = :t",
            "UPDATE tenants SET status_changed_by = NULL WHERE id = :t",
            "DELETE FROM user_tokens WHERE user_id IN (SELECT id FROM users WHERE tenant_id = :t)",
            "DELETE FROM user_sessions WHERE user_id IN (SELECT id FROM users WHERE tenant_id = :t)",
            "DELETE FROM audit_logs WHERE tenant_id = :t OR resource_id = CAST(:t AS text)",
            "DELETE FROM user_facility_memberships WHERE user_id IN (SELECT id FROM users WHERE tenant_id = :t)",
            "DELETE FROM users WHERE tenant_id = :t",
            "DELETE FROM departments WHERE tenant_id = :t",
            "DELETE FROM facilities WHERE tenant_id = :t",
            "DELETE FROM tenants WHERE id = :t",
        ):
            await db.execute(text(sql), p)
    await db.commit()


async def _purge_users(db, usernames):
    for name in usernames:
        p = {"n": name}
        for sql in (
            "DELETE FROM user_tokens WHERE user_id IN (SELECT id FROM users WHERE username = :n)",
            "DELETE FROM user_sessions WHERE user_id IN (SELECT id FROM users WHERE username = :n)",
            "DELETE FROM audit_logs WHERE actor_user_id IN (SELECT id FROM users WHERE username = :n)"
            " OR resource_id IN (SELECT CAST(id AS text) FROM users WHERE username = :n)",
            "DELETE FROM user_facility_memberships WHERE user_id IN (SELECT id FROM users WHERE username = :n)",
            "DELETE FROM users WHERE username = :n",
        ):
            await db.execute(text(sql), p)
    await db.commit()


def login(client, username, password=DEMO, **extra):
    client.cookies.clear()
    return client.post("/api/v1/auth/login", json={"username": username, "password": password, **extra})


def activate_and_login(client, link, username):
    client.cookies.clear()
    token = link.split("token=")[1]
    assert client.post("/api/v1/auth/activate", json={"token": token, "new_password": STRONG}).status_code == 200
    response = login(client, username, STRONG)
    assert response.status_code == 200, response.text
    return response.json()["data"]


@pytest.fixture()
def world(client):
    """Factory for throw-away hospitals (created the real way, by the operator),
    cleaned up afterwards."""
    codes: list[str] = []
    users: list[str] = []

    def make_hospital():
        payload = _payload()
        codes.append(payload["organization"]["code"].upper())
        assert login(client, "super.admin").status_code == 200
        created = client.post("/api/v1/platform/tenants", json=payload)
        assert created.status_code == 201, created.text
        data = created.json()["data"]
        admin = payload["administrator"]["username"]
        session = activate_and_login(client, data["activation_link"], admin)
        facility_a = session["facility"]
        client.cookies.clear()
        return {
            "tenant_id": data["tenant_id"],
            "tenant_code": data["tenant_code"],
            "admin": admin,
            "facility_a": facility_a["id"],
            "payload": payload,
        }

    yield type("World", (), {"make": staticmethod(make_hospital), "users": users})
    client.cookies.clear()
    _run(lambda db: _purge_tenants(db, codes))
    _run(lambda db: _purge_users(db, users))


def _nurse_role_id(client):
    roles = client.get("/api/v1/users/assignable-roles").json()["data"]
    return next(r["id"] for r in roles if r["code"] == "NURSE")


def _facility_body(suffix=None):
    s = suffix or uuid.uuid4().hex[:6].upper()
    return {"name": f"Branch {s}", "facility_code": f"BR-{s}", "facility_type": "clinic"}


def _admin_creates_facility(client):
    body = {**_facility_body(), "phone": "+91 99999 99999", "timezone": "Asia/Kolkata", "currency": "INR"}
    r = client.post("/api/v1/facilities", json=body)
    assert r.status_code == 200, r.text
    return r.json()["data"]


# ============================================================ hierarchy: who can do what


def test_a_hospital_admin_cannot_use_any_platform_endpoint(client, world):
    h = world.make()
    login(client, h["admin"], STRONG)
    tid = h["tenant_id"]
    fid = h["facility_a"]
    calls = [
        ("get", "/platform/organisations", None),
        ("get", f"/platform/organisations/{tid}", None),
        ("patch", f"/platform/organisations/{tid}", {"name": "Hijacked"}),
        ("post", f"/platform/organisations/{tid}/suspend", {"reason": "because I can"}),
        ("post", f"/platform/organisations/{tid}/reactivate", None),
        ("post", f"/platform/organisations/{tid}/facilities", {"facility": _payload()["facility"]}),
        ("post", f"/platform/organisations/{tid}/facilities/{fid}/deactivate", {"reason": "because I can"}),
        ("post", f"/platform/organisations/{tid}/administrators", {"facility_id": fid, "administrator": _payload()["administrator"]}),
    ]
    for method, path, body in calls:
        response = getattr(client, method)(f"/api/v1{path}", **({"json": body} if body is not None else {}))
        assert response.status_code == 403, (method, path, response.status_code)


def test_anonymous_callers_get_401_everywhere_in_the_hierarchy(client):
    client.cookies.clear()
    tid = str(uuid.uuid4())
    for method, path in (
        ("get", "/platform/organisations"),
        ("post", f"/platform/organisations/{tid}/suspend"),
        ("get", "/users"),
        ("post", "/users"),
        ("post", f"/facilities/{tid}/deactivate"),
    ):
        assert getattr(client, method)(f"/api/v1{path}").status_code == 401, path


def test_a_hospital_admin_cannot_create_or_promote_a_super_admin(client, world):
    h = world.make()
    login(client, h["admin"], STRONG)
    roles = client.get("/api/v1/rbac/roles").json()["data"]
    super_role = next(r["id"] for r in roles if r["code"] == "SUPER_ADMIN")

    assignable = {r["code"] for r in client.get("/api/v1/users/assignable-roles").json()["data"]}
    assert "SUPER_ADMIN" not in assignable and "HOSPITAL_ADMIN" in assignable

    invite = client.post(
        "/api/v1/users",
        json={
            "username": f"sneaky.{uuid.uuid4().hex[:6]}",
            "email": f"sneaky.{uuid.uuid4().hex[:6]}@example.org",
            "full_name": "Sneaky Admin",
            "role_id": super_role,
            "facility_ids": [h["facility_a"]],
        },
    )
    assert invite.status_code == 403
    assert invite.json()["error"]["code"] == "ROLE_NOT_ASSIGNABLE"

    # ...nor promote an existing member.
    staff = client.post(
        "/api/v1/users",
        json={
            "username": f"nurse.{uuid.uuid4().hex[:6]}",
            "email": f"nurse.{uuid.uuid4().hex[:6]}@example.org",
            "full_name": "Nina Nurse",
            "role_id": _nurse_role_id(client),
            "facility_ids": [h["facility_a"]],
        },
    ).json()["data"]["user"]
    promote = client.patch(f"/api/v1/users/{staff['id']}", json={"role_id": super_role})
    assert promote.status_code == 403


def test_a_hospital_admin_cannot_see_or_manage_the_platform_operator(client):
    """super.admin shares the demo ForaCare tenant with hospital.admin."""
    login(client, "super.admin")
    operator_id = next(u["id"] for u in client.get("/api/v1/users").json()["data"] if u["username"] == "super.admin")

    login(client, "hospital.admin")
    usernames = {u["username"] for u in client.get("/api/v1/users").json()["data"]}
    assert "super.admin" not in usernames
    assert client.get(f"/api/v1/users/{operator_id}").status_code == 404
    assert client.patch(f"/api/v1/users/{operator_id}", json={"full_name": "Owned"}).status_code == 404
    assert client.post(f"/api/v1/users/{operator_id}/deactivate").status_code == 404
    assert client.post(f"/api/v1/users/{operator_id}/resend-activation").status_code == 404


def test_a_hospital_admin_cannot_reach_another_organisations_users(client, world):
    a, b = world.make(), world.make()
    login(client, b["admin"], STRONG)
    b_user = next(u for u in client.get("/api/v1/users").json()["data"] if u["username"] == b["admin"])

    login(client, a["admin"], STRONG)
    listed = {u["username"] for u in client.get("/api/v1/users").json()["data"]}
    assert b["admin"] not in listed
    uid = b_user["id"]
    assert client.get(f"/api/v1/users/{uid}").status_code == 404
    assert client.patch(f"/api/v1/users/{uid}", json={"full_name": "Owned"}).status_code == 404
    assert client.post(f"/api/v1/users/{uid}/deactivate").status_code == 404
    assert client.post(f"/api/v1/users/{uid}/reactivate").status_code == 404
    # ...nor another organisation's facility.
    assert client.get(f"/api/v1/facilities/{b['facility_a']}").status_code == 404
    assert client.patch(f"/api/v1/facilities/{b['facility_a']}", json={"name": "Owned"}).status_code == 404
    assert client.post(f"/api/v1/facilities/{b['facility_a']}/deactivate", json={"reason": "not mine"}).status_code == 404


def test_a_hospital_admin_cannot_grant_access_to_a_facility_outside_their_organisation(client, world):
    a, b = world.make(), world.make()
    login(client, a["admin"], STRONG)
    role = _nurse_role_id(client)
    body = {
        "username": f"x.{uuid.uuid4().hex[:6]}",
        "email": f"x.{uuid.uuid4().hex[:6]}@example.org",
        "full_name": "Cross Tenant",
        "role_id": role,
    }
    assert client.post("/api/v1/users", json={**body, "facility_ids": [b["facility_a"]]}).status_code == 404
    assert client.post("/api/v1/users", json={**body, "facility_ids": [str(uuid.uuid4())]}).status_code == 404
    assert client.get(f"/api/v1/users?facility_id={b['facility_a']}").status_code == 404


def test_inactive_facilities_cannot_be_assigned(client, world):
    h = world.make()
    login(client, h["admin"], STRONG)
    other = _admin_creates_facility(client)
    assert client.post(f"/api/v1/facilities/{other['id']}/deactivate", json={"reason": "not opening yet"}).status_code == 200
    response = client.post(
        "/api/v1/users",
        json={
            "username": f"n.{uuid.uuid4().hex[:6]}",
            "email": f"n.{uuid.uuid4().hex[:6]}@example.org",
            "full_name": "Nina Nurse",
            "role_id": _nurse_role_id(client),
            "facility_ids": [other["id"]],
        },
    )
    assert response.status_code == 409 and response.json()["error"]["code"] == "FACILITY_INACTIVE"


def test_nobody_can_change_their_own_role_access_or_active_state(client, world):
    h = world.make()
    login(client, h["admin"], STRONG)
    me = next(u for u in client.get("/api/v1/users").json()["data"] if u["username"] == h["admin"])
    nurse = _nurse_role_id(client)
    assert client.patch(f"/api/v1/users/{me['id']}", json={"role_id": nurse}).status_code == 403
    assert client.patch(f"/api/v1/users/{me['id']}", json={"facility_ids": [h["facility_a"]]}).status_code == 403
    assert client.post(f"/api/v1/users/{me['id']}/deactivate").status_code == 403
    # harmless self-service edits are fine
    assert client.patch(f"/api/v1/users/{me['id']}", json={"full_name": "Asha R. Rao"}).status_code == 200


def test_the_last_active_hospital_admin_cannot_be_removed(client, world):
    """Reached by someone who holds users.manage but is not themselves an admin."""
    from app.core.exceptions import ConflictError
    from app.modules.auth.models import User
    from app.modules.users import service as users_service
    from sqlalchemy import select

    h = world.make()
    login(client, h["admin"], STRONG)
    nurse_name = f"manager.{uuid.uuid4().hex[:6]}"
    client.post(
        "/api/v1/users",
        json={
            "username": nurse_name,
            "email": f"{nurse_name}@example.org",
            "full_name": "Pat Manager",
            "role_id": _nurse_role_id(client),
            "facility_ids": [h["facility_a"]],
        },
    )

    async def attempt(db):
        caller = (await db.execute(select(User).where(User.username == nurse_name))).scalar_one()
        admin = (await db.execute(select(User).where(User.username == h["admin"]))).scalar_one()
        for call in (
            lambda: users_service.set_active(db, admin.id, caller, active=False),
        ):
            with pytest.raises(ConflictError) as caught:
                await call()
            assert caught.value.code == "LAST_ADMIN"

    _run(attempt)


# =================================================================== staff lifecycle


def test_a_hospital_admin_invites_staff_who_activate_and_see_only_their_facility(client, world):
    h = world.make()
    login(client, h["admin"], STRONG)
    second = _admin_creates_facility(client)
    username = f"nurse.{uuid.uuid4().hex[:6]}"
    invited = client.post(
        "/api/v1/users",
        json={
            "username": username,
            "email": f"{username}@example.org",
            "full_name": "Nina Nurse",
            "role_id": _nurse_role_id(client),
            "facility_ids": [second["id"]],
        },
    )
    assert invited.status_code == 201, invited.text
    data = invited.json()["data"]
    assert data["user"]["pending_activation"] is True
    assert [f["id"] for f in data["user"]["facilities"]] == [second["id"]]
    assert "/activate-account?token=" in data["activation_link"]

    session = activate_and_login(client, data["activation_link"], username)
    assert session["user"]["role"]["code"] == "NURSE"
    assert session["facility"]["id"] == second["id"]
    assert [f["id"] for f in session["facilities"]] == [second["id"]]
    # a nurse cannot administer anyone
    assert client.get("/api/v1/users").status_code == 403
    # ...nor sign in to the organisation's other facility by naming it
    other_login = login(client, username, STRONG, facility_id=h["facility_a"])
    assert other_login.status_code == 403 and other_login.json()["error"]["code"] == "FACILITY_NOT_ASSIGNED"


def test_staff_listing_can_be_narrowed_to_a_facility(client, world):
    h = world.make()
    login(client, h["admin"], STRONG)
    second = _admin_creates_facility(client)
    username = f"nurse.{uuid.uuid4().hex[:6]}"
    client.post(
        "/api/v1/users",
        json={"username": username, "email": f"{username}@example.org", "full_name": "Nina Nurse",
              "role_id": _nurse_role_id(client), "facility_ids": [second["id"]]},
    )
    at_second = {u["username"] for u in client.get(f"/api/v1/users?facility_id={second['id']}").json()["data"]}
    at_first = {u["username"] for u in client.get(f"/api/v1/users?facility_id={h['facility_a']}").json()["data"]}
    assert username in at_second and username not in at_first
    assert h["admin"] in at_first


def test_deactivating_staff_ends_their_sessions_and_blocks_sign_in(client, world):
    h = world.make()
    login(client, h["admin"], STRONG)
    username = f"nurse.{uuid.uuid4().hex[:6]}"
    link = client.post(
        "/api/v1/users",
        json={"username": username, "email": f"{username}@example.org", "full_name": "Nina Nurse",
              "role_id": _nurse_role_id(client), "facility_ids": [h["facility_a"]]},
    ).json()["data"]
    staff_id = link["user"]["id"]
    activate_and_login(client, link["activation_link"], username)
    staff_cookies = dict(client.cookies)
    assert client.get("/api/v1/auth/me").status_code == 200

    login(client, h["admin"], STRONG)
    assert client.post(f"/api/v1/users/{staff_id}/deactivate").status_code == 200
    assert client.post(f"/api/v1/users/{staff_id}/deactivate").status_code == 409  # already

    client.cookies.clear()
    client.cookies.update(staff_cookies)
    assert client.get("/api/v1/auth/me").status_code == 401  # session revoked
    refused = login(client, username, STRONG)
    assert refused.status_code == 401 and refused.json()["error"]["code"] == "ACCOUNT_DISABLED"

    login(client, h["admin"], STRONG)
    assert client.post(f"/api/v1/users/{staff_id}/reactivate").status_code == 200
    assert login(client, username, STRONG).status_code == 200


def test_changing_a_role_or_facilities_takes_effect_immediately(client, world):
    h = world.make()
    login(client, h["admin"], STRONG)
    second = _admin_creates_facility(client)
    username = f"nurse.{uuid.uuid4().hex[:6]}"
    invited = client.post(
        "/api/v1/users",
        json={"username": username, "email": f"{username}@example.org", "full_name": "Nina Nurse",
              "role_id": _nurse_role_id(client), "facility_ids": [h["facility_a"], second["id"]],
              "default_facility_id": second["id"]},
    ).json()["data"]
    staff_id = invited["user"]["id"]
    assert invited["user"]["facilities"][0]["id"] == second["id"]  # default first
    activate_and_login(client, invited["activation_link"], username)
    staff_cookies = dict(client.cookies)

    login(client, h["admin"], STRONG)
    updated = client.patch(f"/api/v1/users/{staff_id}", json={"facility_ids": [h["facility_a"]]})
    assert updated.status_code == 200
    assert [f["id"] for f in updated.json()["data"]["facilities"]] == [h["facility_a"]]

    client.cookies.clear()
    client.cookies.update(staff_cookies)  # was working in `second`, no longer a member
    assert client.get("/api/v1/auth/me").status_code == 401


def test_duplicate_staff_details_are_refused_field_by_field(client, world):
    h = world.make()
    login(client, h["admin"], STRONG)
    body = {"username": h["admin"], "email": h["payload"]["administrator"]["email"], "full_name": "Dup Licate",
            "role_id": _nurse_role_id(client), "facility_ids": [h["facility_a"]]}
    response = client.post("/api/v1/users", json=body)
    assert response.status_code == 409
    assert {d["field"] for d in response.json()["error"]["details"]} == {"username", "email"}


def test_resending_an_activation_link_only_works_before_first_sign_in(client, world):
    h = world.make()
    login(client, h["admin"], STRONG)
    username = f"nurse.{uuid.uuid4().hex[:6]}"
    invited = client.post(
        "/api/v1/users",
        json={"username": username, "email": f"{username}@example.org", "full_name": "Nina Nurse",
              "role_id": _nurse_role_id(client), "facility_ids": [h["facility_a"]]},
    ).json()["data"]
    again = client.post(f"/api/v1/users/{invited['user']['id']}/resend-activation")
    assert again.status_code == 200
    new_link = again.json()["data"]["activation_link"]
    assert new_link != invited["activation_link"]
    # the old link no longer works; the new one does
    client.cookies.clear()
    assert client.post("/api/v1/auth/activate", json={"token": invited["activation_link"].split("token=")[1], "new_password": STRONG}).status_code == 401
    activate_and_login(client, new_link, username)
    login(client, h["admin"], STRONG)
    assert client.post(f"/api/v1/users/{invited['user']['id']}/resend-activation").status_code == 409


# ================================================================ tenant lifecycle


def test_operator_lists_and_inspects_organisations(client, world):
    h = world.make()
    login(client, "super.admin")
    listed = client.get("/api/v1/platform/organisations").json()["data"]
    mine = next(t for t in listed if t["id"] == h["tenant_id"])
    assert mine["is_active"] is True and mine["facility_count"] == 1 and mine["user_count"] == 1
    detail = client.get(f"/api/v1/platform/organisations/{h['tenant_id']}").json()["data"]
    assert [a["username"] for a in detail["administrators"]] == [h["admin"]]
    assert len(detail["facilities"]) == 1
    assert client.get(f"/api/v1/platform/organisations/{uuid.uuid4()}").status_code == 404


def test_operator_can_rename_but_not_recode_an_organisation(client, world):
    h = world.make()
    login(client, "super.admin")
    response = client.patch(
        f"/api/v1/platform/organisations/{h['tenant_id']}", json={"name": "Renamed Hospital Group", "code": "HACKED"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Renamed Hospital Group"
    assert response.json()["data"]["code"] == h["tenant_code"]  # code is immutable
    # recorded in the renamed organisation's own audit log
    login(client, h["admin"], STRONG)
    logs = client.get("/api/v1/audit/logs?limit=30").json()["data"]
    assert any(l["action"] == "platform.tenant_updated" for l in logs)


def test_suspending_an_organisation_locks_everyone_out_and_is_reversible(client, world):
    h = world.make()
    login(client, h["admin"], STRONG)
    admin_cookies = dict(client.cookies)
    assert client.get("/api/v1/auth/me").status_code == 200

    login(client, "super.admin")
    assert client.post(f"/api/v1/platform/organisations/{h['tenant_id']}/suspend", json={"reason": "no"}).status_code == 422
    suspended = client.post(
        f"/api/v1/platform/organisations/{h['tenant_id']}/suspend", json={"reason": "Contract ended 2026-10-01"}
    )
    assert suspended.status_code == 200
    assert suspended.json()["data"]["is_active"] is False
    assert suspended.json()["data"]["status_reason"] == "Contract ended 2026-10-01"
    assert client.post(f"/api/v1/platform/organisations/{h['tenant_id']}/suspend", json={"reason": "Again, again"}).status_code == 409

    client.cookies.clear()
    client.cookies.update(admin_cookies)
    assert client.get("/api/v1/auth/me").status_code == 401  # live session ended
    refused = login(client, h["admin"], STRONG)
    assert refused.status_code == 401 and refused.json()["error"]["code"] == "ACCOUNT_DISABLED"

    login(client, "super.admin")
    assert client.post(f"/api/v1/platform/organisations/{h['tenant_id']}/reactivate").status_code == 200
    assert client.post(f"/api/v1/platform/organisations/{h['tenant_id']}/reactivate").status_code == 409
    assert login(client, h["admin"], STRONG).status_code == 200


def test_suspension_is_audited_in_the_suspended_organisations_own_log(client, world):
    h = world.make()
    login(client, "super.admin")
    client.post(f"/api/v1/platform/organisations/{h['tenant_id']}/suspend", json={"reason": "Non-payment, notice sent"})
    client.post(f"/api/v1/platform/organisations/{h['tenant_id']}/reactivate")
    login(client, h["admin"], STRONG)
    actions = [l["action"] for l in client.get("/api/v1/audit/logs?limit=50").json()["data"]]
    assert "platform.tenant_suspended" in actions and "platform.tenant_reactivated" in actions


def test_the_operator_cannot_suspend_their_own_organisation(client):
    login(client, "super.admin")
    tenants = client.get("/api/v1/platform/organisations").json()["data"]
    own = next(t for t in tenants if t["code"] == "FORACARE")
    response = client.post(f"/api/v1/platform/organisations/{own['id']}/suspend", json={"reason": "Oops, wrong one"})
    assert response.status_code == 409 and response.json()["error"]["code"] == "TENANT_SELF_SUSPEND"
    assert client.get("/api/v1/auth/me").status_code == 200


def test_a_suspended_organisation_cannot_gain_facilities_or_administrators(client, world):
    h = world.make()
    login(client, "super.admin")
    client.post(f"/api/v1/platform/organisations/{h['tenant_id']}/suspend", json={"reason": "Under investigation"})
    fac = client.post(f"/api/v1/platform/organisations/{h['tenant_id']}/facilities", json={"facility": _payload()["facility"]})
    assert fac.status_code == 409 and fac.json()["error"]["code"] == "TENANT_SUSPENDED"
    adm = client.post(
        f"/api/v1/platform/organisations/{h['tenant_id']}/administrators",
        json={"facility_id": h["facility_a"], "administrator": _payload()["administrator"]},
    )
    assert adm.status_code == 409


def test_operator_adds_a_facility_to_any_organisation(client, world):
    h = world.make()
    login(client, "super.admin")
    facility = _payload()["facility"]
    created = client.post(f"/api/v1/platform/organisations/{h['tenant_id']}/facilities", json={"facility": facility})
    assert created.status_code == 201, created.text
    assert created.json()["data"]["facility_type"] == "medical_centre"
    dup = client.post(f"/api/v1/platform/organisations/{h['tenant_id']}/facilities", json={"facility": facility})
    assert dup.status_code == 409 and dup.json()["error"]["details"][0]["field"] == "facility.facility_code"
    detail = client.get(f"/api/v1/platform/organisations/{h['tenant_id']}").json()["data"]
    assert detail["facility_count"] == 2


def test_operator_assigns_an_additional_hospital_admin_via_an_audited_workflow(client, world):
    h = world.make()
    login(client, "super.admin")
    s = uuid.uuid4().hex[:6]
    body = {
        "facility_id": h["facility_a"],
        "administrator": {"full_name": "Second Admin", "username": f"admin2.{s}", "email": f"admin2.{s}@example.org"},
    }
    assigned = client.post(f"/api/v1/platform/organisations/{h['tenant_id']}/administrators", json=body)
    assert assigned.status_code == 201, assigned.text
    data = assigned.json()["data"]
    assert "password" not in assigned.text.lower().replace("choose your password", "")
    session = activate_and_login(client, data["activation_link"], f"admin2.{s}")
    assert session["user"]["role"]["code"] == "HOSPITAL_ADMIN"
    assert session["tenant"]["id"] == h["tenant_id"]

    actions = [l["action"] for l in client.get("/api/v1/audit/logs?limit=30").json()["data"]]
    assert "platform.administrator_assigned" in actions  # in the organisation's own log (second admin can read it)
    login(client, "super.admin")
    # a facility from another organisation is never accepted
    other = world.make()
    login(client, "super.admin")
    foreign = client.post(
        f"/api/v1/platform/organisations/{h['tenant_id']}/administrators",
        json={**body, "facility_id": other["facility_a"],
              "administrator": {"full_name": "Third Admin", "username": f"admin3.{s}", "email": f"admin3.{s}@example.org"}},
    )
    assert foreign.status_code == 404
    clash = client.post(f"/api/v1/platform/organisations/{h['tenant_id']}/administrators", json=body)
    assert clash.status_code == 409


# ============================================================== facility lifecycle


def test_deactivating_a_facility_locks_out_its_staff_and_is_reversible(client, world):
    h = world.make()
    login(client, h["admin"], STRONG)
    second = _admin_creates_facility(client)
    username = f"nurse.{uuid.uuid4().hex[:6]}"
    invited = client.post(
        "/api/v1/users",
        json={"username": username, "email": f"{username}@example.org", "full_name": "Nina Nurse",
              "role_id": _nurse_role_id(client), "facility_ids": [second["id"]]},
    ).json()["data"]
    activate_and_login(client, invited["activation_link"], username)
    nurse_cookies = dict(client.cookies)

    login(client, h["admin"], STRONG)
    done = client.post(f"/api/v1/facilities/{second['id']}/deactivate", json={"reason": "Renovation until March"})
    assert done.status_code == 200 and done.json()["data"]["is_active"] is False
    assert done.json()["data"]["status_reason"] == "Renovation until March"

    client.cookies.clear()
    client.cookies.update(nurse_cookies)
    assert client.get("/api/v1/auth/me").status_code == 401  # their facility is gone
    refused = login(client, username, STRONG)
    assert refused.status_code == 401 and refused.json()["error"]["code"] == "NO_FACILITY_ACCESS"

    login(client, h["admin"], STRONG)
    assert client.post(f"/api/v1/facilities/{second['id']}/reactivate").status_code == 200
    assert login(client, username, STRONG).status_code == 200


def test_a_facility_cannot_be_deactivated_while_you_work_in_it_or_if_it_is_the_last(client, world):
    h = world.make()
    login(client, h["admin"], STRONG)
    here = client.post(f"/api/v1/facilities/{h['facility_a']}/deactivate", json={"reason": "Closing the only one"})
    assert here.status_code == 409 and here.json()["error"]["code"] == "FACILITY_IN_USE"

    # The operator is not "in" the facility, so the last-active-facility rule is what stops them.
    login(client, "super.admin")
    last = client.post(
        f"/api/v1/platform/organisations/{h['tenant_id']}/facilities/{h['facility_a']}/deactivate",
        json={"reason": "Closing the only one"},
    )
    assert last.status_code == 409 and last.json()["error"]["code"] == "LAST_ACTIVE_FACILITY"


def test_open_clinical_work_blocks_deactivation(client, world, monkeypatch):
    from app.modules.lifecycle import service as lifecycle

    h = world.make()
    login(client, h["admin"], STRONG)
    second = _admin_creates_facility(client)

    async def busy(db, facility):
        return [("admissions", "2 patient(s) are currently admitted. Discharge or transfer them first."),
                ("opd_queue", "5 OPD token(s) are still open. Complete or cancel them first.")]

    monkeypatch.setattr(lifecycle, "_open_work", busy)
    response = client.post(f"/api/v1/facilities/{second['id']}/deactivate", json={"reason": "Closing for the year"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "FACILITY_HAS_OPEN_WORK"
    assert {d["field"] for d in response.json()["error"]["details"]} == {"admissions", "opd_queue"}
    # still active
    assert client.get(f"/api/v1/facilities/{second['id']}").json()["data"]["is_active"] is True


def test_the_open_work_check_runs_real_queries_and_an_empty_facility_has_none(client, world):
    from app.modules.facilities.models import Facility
    from app.modules.lifecycle import service as lifecycle
    from sqlalchemy import select

    h = world.make()

    async def check(db):
        facility = (await db.execute(select(Facility).where(Facility.id == uuid.UUID(h["facility_a"])))).scalar_one()
        return await lifecycle._open_work(db, facility)

    assert _run(check) == []


def test_a_reason_is_required_and_activation_state_is_not_patchable(client, world):
    h = world.make()
    login(client, h["admin"], STRONG)
    second = _admin_creates_facility(client)
    assert client.post(f"/api/v1/facilities/{second['id']}/deactivate", json={"reason": "x"}).status_code == 422
    assert client.post(f"/api/v1/facilities/{second['id']}/deactivate", json={}).status_code == 422
    patched = client.patch(f"/api/v1/facilities/{second['id']}", json={"is_active": False})
    assert patched.status_code == 200 and patched.json()["data"]["is_active"] is True


def test_creating_a_facility_gives_the_creator_access_to_it(client, world):
    h = world.make()
    login(client, h["admin"], STRONG)
    second = _admin_creates_facility(client)
    me = client.get("/api/v1/auth/me").json()["data"]
    assert second["id"] in {f["id"] for f in me["facilities"]}
    switched = client.post("/api/v1/auth/switch-facility", json={"facility_id": second["id"]})
    assert switched.status_code == 200 and switched.json()["data"]["facility"]["id"] == second["id"]


def test_facility_lifecycle_is_audited(client, world):
    h = world.make()
    login(client, h["admin"], STRONG)
    second = _admin_creates_facility(client)
    client.post(f"/api/v1/facilities/{second['id']}/deactivate", json={"reason": "Planned closure"})
    client.post(f"/api/v1/facilities/{second['id']}/reactivate")
    actions = [l["action"] for l in client.get("/api/v1/audit/logs?limit=50").json()["data"]]
    assert {"facilities.created", "facilities.deactivated", "facilities.reactivated"} <= set(actions)


# ===================================================== facility context is never trusted


def test_a_client_supplied_facility_id_cannot_widen_access_within_an_organisation(client, world):
    """Resources are bound to the session's facility; naming another facility in a
    query or body changes nothing."""
    h = world.make()
    login(client, h["admin"], STRONG)
    second = _admin_creates_facility(client)
    dept = client.post(
        f"/api/v1/departments?facility_id={second['id']}",
        json={"name": "Cardiology", "code": "CARD", "description": "x", "facility_id": second["id"]},
    )
    assert dept.status_code == 200, dept.text
    assert dept.json()["data"]["facility_id"] == h["facility_a"]  # the session's facility, not the named one
    # Not visible once the admin works in the other facility.
    client.post("/api/v1/auth/switch-facility", json={"facility_id": second["id"]})
    assert client.get("/api/v1/departments").json()["data"] == []
    assert client.get(f"/api/v1/departments/{dept.json()['data']['id']}").status_code == 404
    assert client.get(f"/api/v1/departments?facility_id={h['facility_a']}").json()["data"] == []


def test_patient_records_are_confined_to_the_registering_facility(client):
    """P10-B02 closes two same-organisation gaps: reading/updating a patient by id from
    another facility, and the duplicate check returning another facility's records."""
    n = uuid.uuid4().int % 10**9
    mobile = f"9{n:09d}"[:10]
    body = {
        "first_name": "Facility", "last_name": f"Scope{n}", "gender": "FEMALE", "dob": "1991-02-03",
        "blood_group": "O_POSITIVE",
        "address": {"street": "1 St", "city": "Pune", "state": "MH", "pincode": "411001"},
        "contacts": [{"contact_type": "MOBILE", "value": mobile, "is_primary": True}],
        "identifiers": [],
    }
    login(client, "dr.priya")  # registers at FC-MAIN-01 (hospital admins cannot register patients)
    created = client.post("/api/v1/patients", json=body)
    assert created.status_code == 200, created.text
    patient_id = created.json()["data"]["id"]

    login(client, "hospital.admin")  # administers the whole organisation
    south = next((f for f in client.get("/api/v1/facilities").json()["data"] if f["facility_code"] == "FC-ST-02"), None)
    assert south is not None

    # A same-organisation front-desk user working in the other facility, created the supported way.
    username = f"scope.admin.{uuid.uuid4().hex[:6]}"
    roles = client.get("/api/v1/users/assignable-roles").json()["data"]
    receptionist_role = next(r["id"] for r in roles if r["code"] == "RECEPTIONIST")  # holds patients.manage
    invited = client.post(
        "/api/v1/users",
        json={"username": username, "email": f"{username}@example.org", "full_name": "South Desk",
              "role_id": receptionist_role, "facility_ids": [south["id"]]},
    )
    assert invited.status_code == 201, invited.text
    try:
        activate_and_login(client, invited.json()["data"]["activation_link"], username)
        assert client.get("/api/v1/auth/me").json()["data"]["facility"]["id"] == south["id"]
        assert client.get(f"/api/v1/patients/{patient_id}").status_code == 404
        assert client.patch(f"/api/v1/patients/{patient_id}", json={"occupation": "Spy"}).status_code == 404
        dup = client.post("/api/v1/patients/check-duplicates", json={"mobile": mobile})
        assert dup.status_code == 200 and dup.json()["data"] == []  # nothing disclosed across facilities
        # registration is still refused organisation-wide, without revealing who
        refused = client.post("/api/v1/patients", json=body)
        assert refused.status_code == 409 and "Scope" not in refused.text
    finally:
        client.cookies.clear()
        _run(lambda db: _purge_users(db, [username]))

    login(client, "dr.priya")  # back at the registering facility everything resolves
    assert client.get(f"/api/v1/patients/{patient_id}").status_code == 200
    assert client.post("/api/v1/patients/check-duplicates", json={"mobile": mobile}).json()["data"]


def test_cross_facility_matrix_within_one_organisation(client):
    """For every module, ids that belong to FC-MAIN-01 are never served to a fully
    privileged Hospital Admin who works in FC-ST-02 (same organisation)."""
    from tests.test_tenant_isolation_matrix import MODULES, _ids, _no_leak

    login(client, "hospital.admin")
    south = next(f for f in client.get("/api/v1/facilities").json()["data"] if f["facility_code"] == "FC-ST-02")
    main_ids = {
        module: [i for i in _ids(client, path)]
        for module, (path, _) in MODULES.items()
        if module != "facilities"
    }

    username = f"matrix.admin.{uuid.uuid4().hex[:6]}"
    roles = client.get("/api/v1/users/assignable-roles").json()["data"]
    role_id = next(r["id"] for r in roles if r["code"] == "HOSPITAL_ADMIN")
    invited = client.post(
        "/api/v1/users",
        json={"username": username, "email": f"{username}@example.org", "full_name": "Matrix Admin",
              "role_id": role_id, "facility_ids": [south["id"]]},
    ).json()["data"]
    probed = 0
    try:
        activate_and_login(client, invited["activation_link"], username)
        for module, (list_path, details) in MODULES.items():
            if module == "facilities":
                continue
            # the admin's own list never contains FC-MAIN-01 rows
            assert not (set(_ids(client, list_path)) & set(main_ids[module])), module
            for resource_id in main_ids[module]:
                for template in details:
                    response = client.get("/api/v1" + template.format(id=resource_id))
                    assert _no_leak(response), (module, template, response.status_code)
                    probed += 1
    finally:
        client.cookies.clear()
        _run(lambda db: _purge_users(db, [username]))
    assert probed > 0, "the matrix found nothing to probe"
