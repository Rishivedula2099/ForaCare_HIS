"""P10-F02: only an authenticated platform operator can create a hospital; setup
is atomic, validated, and refuses duplicates."""
import asyncio
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

PASSWORD = "Demo@123"
URL = "/api/v1/platform/tenants"


def _login(client, username):
    return client.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})


def _run(coro_factory):
    async def runner():
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        try:
            async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as db:
                return await coro_factory(db)
        finally:
            await engine.dispose()

    return asyncio.run(runner())


def _payload(suffix=None, **overrides):
    s = suffix or uuid.uuid4().hex[:8]
    body = {
        "organization": {"name": f"Green Valley {s}", "code": f"gv{s}"},
        "facility": {
            "name": f"Green Valley Main {s}",
            "facility_code": f"gv-main-{s}",
            "facility_type": "medical_centre",
            "phone": "+91 98765 43210",
            "email": f"info.{s}@greenvalley.example",
            "address_line1": "12 Lake Road",
            "address_line2": "Indiranagar",
            "city": "Bengaluru",
            "state": "Karnataka",
            "postal_code": "560038",
            "timezone": "Asia/Kolkata",
            "currency": "INR",
        },
        "administrator": {
            "full_name": "Asha Rao",
            "username": f"asha.{s}",
            "email": f"asha.{s}@greenvalley.example",
        },
        "send_activation_email": False,
    }
    for key, value in overrides.items():
        section, _, field = key.partition("__")
        if field:
            body[section][field] = value
        else:
            body[section] = value
    return body


async def _purge(db, tenant_codes):
    for code in tenant_codes:
        row = (await db.execute(text("SELECT id FROM tenants WHERE code = :c"), {"c": code})).first()
        if row is None:
            continue
        p = {"t": row[0]}
        for sql in (
            "DELETE FROM user_tokens WHERE user_id IN (SELECT id FROM users WHERE tenant_id = :t)",
            "DELETE FROM user_sessions WHERE user_id IN (SELECT id FROM users WHERE tenant_id = :t)",
            "DELETE FROM audit_logs WHERE tenant_id = :t OR resource_id = CAST(:t AS text)",
            "DELETE FROM user_facility_memberships WHERE user_id IN (SELECT id FROM users WHERE tenant_id = :t)",
            "DELETE FROM users WHERE tenant_id = :t",
            "DELETE FROM facilities WHERE tenant_id = :t",
            "DELETE FROM tenants WHERE id = :t",
        ):
            await db.execute(text(sql), p)
    await db.commit()


@pytest.fixture()
def cleanup():
    codes: list[str] = []
    yield codes
    _run(lambda db: _purge(db, codes))


# ------------------------------------------------------------------ access control


def test_anonymous_cannot_create_a_tenant(client):
    assert client.post(URL, json=_payload()).status_code == 401
    assert client.get("/api/v1/platform/setup-options").status_code == 401
    assert client.get("/api/v1/platform/setup/availability?facility_code=X1").status_code == 401


@pytest.mark.parametrize("username", ["hospital.admin", "dr.priya", "receptionist", "auditor", "sunrise.admin"])
def test_non_operators_are_refused(client, username):
    _login(client, username)
    assert client.post(URL, json=_payload()).status_code == 403
    assert client.get("/api/v1/platform/setup-options").status_code == 403


def test_a_hospital_admin_cannot_grant_themselves_platform_power(client):
    """roles.manage must not become a route to creating tenants."""
    _login(client, "hospital.admin")
    perms = client.get("/api/v1/rbac/permissions").json()["data"]
    tenants_manage = next(p["id"] for p in perms if p["code"] == "tenants.manage")
    roles = client.get("/api/v1/rbac/roles").json()["data"]
    hospital_admin = next(r for r in roles if r["code"] == "HOSPITAL_ADMIN")
    current = client.get(f"/api/v1/rbac/roles/{hospital_admin['id']}").json()["data"]["permissions"]

    response = client.patch(
        f"/api/v1/rbac/roles/{hospital_admin['id']}/permissions",
        json={"permission_ids": [p["id"] for p in current] + [tenants_manage]},
    )
    assert response.status_code == 403
    assert client.post(URL, json=_payload()).status_code == 403


def test_the_platform_operator_role_cannot_be_edited(client):
    _login(client, "hospital.admin")
    roles = client.get("/api/v1/rbac/roles").json()["data"]
    super_admin = next(r for r in roles if r["code"] == "SUPER_ADMIN")
    response = client.patch(f"/api/v1/rbac/roles/{super_admin['id']}/permissions", json={"permission_ids": []})
    assert response.status_code == 403


def test_a_denied_attempt_is_audited(client):
    _login(client, "dr.priya")
    client.post(URL, json=_payload())
    _login(client, "hospital.admin")
    logs = client.get("/api/v1/audit/logs?limit=50").json()["data"]
    assert any(log["action"] == "security.permission_denied" and "/platform/tenants" in str(log["after"]) for log in logs)


# ---------------------------------------------------------------------- happy path


def test_operator_creates_tenant_facility_and_admin_who_can_activate_and_sign_in(client, cleanup):
    payload = _payload()
    cleanup.append(payload["organization"]["code"].upper())
    _login(client, "super.admin")

    response = client.post(URL, json=payload)
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["tenant_code"] == payload["organization"]["code"].upper()  # normalised
    assert data["facility_code"] == payload["facility"]["facility_code"].upper()
    assert data["facility_type"] == "medical_centre"
    assert "/activate-account?token=" in data["activation_link"]
    assert data["activation_email_sent"] is False

    # Everything captured is persisted on the facility record.
    client.cookies.clear()
    token = data["activation_link"].split("token=")[1]
    assert client.post("/api/v1/auth/activate", json={"token": token, "new_password": "Str0ng!Passw0rd#9"}).status_code == 200
    login = client.post(
        "/api/v1/auth/login", json={"username": payload["administrator"]["username"], "password": "Str0ng!Passw0rd#9"}
    )
    assert login.status_code == 200
    body = login.json()["data"]
    assert body["user"]["role"]["code"] == "HOSPITAL_ADMIN"
    facility = body["facility"]
    assert facility["facility_type"] == "medical_centre"
    assert facility["timezone"] == "Asia/Kolkata" and facility["currency"] == "INR"
    assert facility["phone"] == "+91 98765 43210"
    assert facility["address"] == "12 Lake Road, Indiranagar, Bengaluru, Karnataka 560038"
    assert body["tenant"]["code"] == data["tenant_code"]


def test_the_new_hospital_is_isolated_from_the_operators_tenant(client, cleanup):
    payload = _payload()
    cleanup.append(payload["organization"]["code"].upper())
    _login(client, "super.admin")
    created = client.post(URL, json=payload).json()["data"]
    operator_facilities = client.get("/api/v1/facilities").json()["data"]
    assert created["facility_id"] not in {f["id"] for f in operator_facilities}


def test_setup_is_audited(client, cleanup):
    payload = _payload()
    cleanup.append(payload["organization"]["code"].upper())
    _login(client, "super.admin")
    client.post(URL, json=payload)
    logs = client.get("/api/v1/audit/logs?limit=20").json()["data"]
    assert any(log["action"] == "platform.tenant_created" for log in logs)


def test_the_response_never_contains_a_password_or_hash(client, cleanup):
    payload = _payload()
    cleanup.append(payload["organization"]["code"].upper())
    _login(client, "super.admin")
    text_ = client.post(URL, json=payload).text.lower()
    assert "password_hash" not in text_ and "$2b$" not in text_


def test_setup_options_are_served_to_the_wizard(client):
    _login(client, "super.admin")
    data = client.get("/api/v1/platform/setup-options").json()["data"]
    assert {o["value"] for o in data["facility_types"]} == {"hospital", "clinic", "medical_centre"}
    assert "Asia/Kolkata" in {o["value"] for o in data["timezones"]}
    assert "INR" in {o["value"] for o in data["currencies"]}
    assert isinstance(data["email_delivery_available"], bool)


# ------------------------------------------------------------------- validation


@pytest.mark.parametrize(
    ("override", "field"),
    [
        ({"organization__name": ""}, "organization.name"),
        ({"organization__code": "x"}, "organization.code"),
        ({"organization__code": "has space"}, "organization.code"),
        ({"facility__name": " "}, "facility.name"),
        ({"facility__facility_type": "pharmacy"}, "facility.facility_type"),
        ({"facility__phone": "abc"}, "facility.phone"),
        ({"facility__email": "nope"}, "facility.email"),
        ({"facility__address_line1": ""}, "facility.address_line1"),
        ({"facility__city": ""}, "facility.city"),
        ({"facility__postal_code": "!!"}, "facility.postal_code"),
        ({"facility__timezone": "Mars/Olympus"}, "facility.timezone"),
        ({"facility__currency": "XXX"}, "facility.currency"),
        ({"administrator__username": "a b"}, "administrator.username"),
        ({"administrator__email": "someone@clinic.test"}, "administrator.email"),  # reserved domain
        ({"administrator__full_name": ""}, "administrator.full_name"),
    ],
)
def test_incomplete_or_invalid_submissions_are_rejected_with_the_field(client, override, field):
    _login(client, "super.admin")
    response = client.post(URL, json=_payload(**override))
    assert response.status_code == 422
    fields = {d["field"] for d in response.json()["error"]["details"]}
    assert any(f.endswith(field) for f in fields), fields


def test_missing_sections_are_rejected(client):
    _login(client, "super.admin")
    for section in ("organization", "facility", "administrator"):
        body = _payload()
        del body[section]
        assert client.post(URL, json=body).status_code == 422


def test_an_invalid_submission_creates_nothing(client):
    payload = _payload(facility__timezone="Mars/Olympus")
    _login(client, "super.admin")
    assert client.post(URL, json=payload).status_code == 422
    code = payload["organization"]["code"].upper()
    count = _run(lambda db: db.execute(text("SELECT count(*) FROM tenants WHERE code = :c"), {"c": code}))
    assert count.scalar_one() == 0


# -------------------------------------------------------------------- duplicates


def test_resubmitting_the_same_setup_is_refused_and_creates_one_hospital(client, cleanup):
    payload = _payload()
    cleanup.append(payload["organization"]["code"].upper())
    _login(client, "super.admin")
    assert client.post(URL, json=payload).status_code == 201
    again = client.post(URL, json=payload)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "DUPLICATE"
    code = payload["organization"]["code"].upper()
    count = _run(lambda db: db.execute(text("SELECT count(*) FROM tenants WHERE code = :c"), {"c": code}))
    assert count.scalar_one() == 1


def test_every_clash_is_reported_at_once_per_field(client, cleanup):
    first = _payload()
    cleanup.append(first["organization"]["code"].upper())
    _login(client, "super.admin")
    assert client.post(URL, json=first).status_code == 201

    clash = _payload(
        organization__code=first["organization"]["code"],
        facility__facility_code=first["facility"]["facility_code"],
        administrator__username=first["administrator"]["username"],
        administrator__email=first["administrator"]["email"],
    )
    response = client.post(URL, json=clash)
    assert response.status_code == 409
    fields = {d["field"] for d in response.json()["error"]["details"]}
    assert fields == {
        "organization.code",
        "facility.facility_code",
        "administrator.username",
        "administrator.email",
    }


def test_codes_are_case_insensitive_for_duplicate_detection(client, cleanup):
    first = _payload()
    cleanup.append(first["organization"]["code"].upper())
    _login(client, "super.admin")
    assert client.post(URL, json=first).status_code == 201
    shouting = _payload(organization__code=first["organization"]["code"].upper(), administrator__email=first["administrator"]["email"].upper())
    assert client.post(URL, json=shouting).status_code == 409


def test_a_clash_with_existing_demo_data_is_refused(client):
    _login(client, "super.admin")
    response = client.post(URL, json=_payload(administrator__username="dr.priya", organization__code="FORACARE"))
    assert response.status_code == 409


def test_concurrent_duplicate_submissions_create_exactly_one_hospital(cleanup):
    """Two near-simultaneous submits (double click, two tabs) race past the
    pre-check; the unique constraints decide, one wins and the other is told."""
    from app.core.exceptions import ConflictError
    from app.modules.platform.schemas import TenantSetupRequest
    from app.modules.platform.service import create_tenant_with_facility

    payload = _payload()
    cleanup.append(payload["organization"]["code"].upper())
    request = TenantSetupRequest.model_validate(payload)

    async def race():
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async def attempt():
            async with factory() as db:
                try:
                    await create_tenant_with_facility(db, request, None)  # operator is only for the audit actor
                    return "created"
                except ConflictError:
                    return "conflict"

        try:
            return await asyncio.gather(attempt(), attempt())
        finally:
            await engine.dispose()

    assert sorted(asyncio.run(race())) == ["conflict", "created"]
    count = _run(lambda db: db.execute(text("SELECT count(*) FROM tenants WHERE code = :c"), {"c": payload["organization"]["code"].upper()}))
    assert count.scalar_one() == 1


def test_availability_reports_what_is_taken(client):
    _login(client, "super.admin")
    taken = client.get(
        "/api/v1/platform/setup/availability?organization_code=foracare&facility_code=fc-main-01&username=dr.priya&email=super.admin@foracare-his.com"
    ).json()["data"]
    assert taken == {"organization_code": False, "facility_code": False, "username": False, "email": False}
    free = client.get(
        f"/api/v1/platform/setup/availability?organization_code=free{uuid.uuid4().hex[:6]}&username=nobody{uuid.uuid4().hex[:6]}"
    ).json()["data"]
    assert free["organization_code"] is True and free["username"] is True
    assert free["facility_code"] is None and free["email"] is None  # not asked


def test_a_super_admin_account_cannot_be_created_through_the_api(client):
    """The wizard only ever creates HOSPITAL_ADMIN; a role field is not accepted."""
    _login(client, "super.admin")
    body = _payload()
    body["administrator"]["role"] = "SUPER_ADMIN"
    response = client.post(URL, json=body)
    if response.status_code == 201:
        client.cookies.clear()
        token = response.json()["data"]["activation_link"].split("token=")[1]
        client.post("/api/v1/auth/activate", json={"token": token, "new_password": "Str0ng!Passw0rd#9"})
        login = client.post(
            "/api/v1/auth/login", json={"username": body["administrator"]["username"], "password": "Str0ng!Passw0rd#9"}
        )
        assert login.json()["data"]["user"]["role"]["code"] == "HOSPITAL_ADMIN"
        _run(lambda db: _purge(db, [body["organization"]["code"].upper()]))
