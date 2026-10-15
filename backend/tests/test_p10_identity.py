"""P10-B01 / P10-F01: no shipped credentials, DB-backed memberships, activation
and password-reset links, facility switching, public onboarding enquiries."""
import asyncio
import re
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import Settings, get_settings
from app.modules.auth.provisioning import provision_admin
from tests.prod_settings import prod_kwargs

MIGRATIONS = Path(__file__).resolve().parent.parent / "migrations" / "versions"
HOSPITAL_ADMIN = "hospital.admin"
DEMO_PASSWORD = "Demo@123"
NEW_PASSWORD = "Str0ng!Passw0rd"


def _login(client, username, password=DEMO_PASSWORD, facility_id=None):
    body = {"username": username, "password": password}
    if facility_id:
        body["facility_id"] = facility_id
    return client.post("/api/v1/auth/login", json=body)


# ---------------------------------------------------------------- demo seeds


def test_demo_seed_flag_is_refused_outside_local():
    with pytest.raises(ValueError, match="SEED_DEMO_DATA"):
        Settings(**prod_kwargs(seed_demo_data=True))


def test_demo_seed_is_off_unless_explicitly_enabled():
    assert Settings(_env_file=None).seed_demo_data is False


def test_every_migration_that_ships_demo_credentials_is_gated():
    """A migration that mentions the shared demo password or a demo id must
    only act when `demo_seed_enabled()` says so."""
    markers = re.compile(r"Demo@123|11111111-1111-1111|66666666-6666|33333333-3333")
    offenders = []
    for path in MIGRATIONS.glob("*.py"):
        source = path.read_text(encoding="utf8")
        if markers.search(source) and "demo_seed_enabled" not in source:
            offenders.append(path.name)
    assert not offenders, offenders


# ------------------------------------------------------------ DB test helpers


def _engine():
    return create_async_engine(get_settings().database_url, poolclass=NullPool)


def _run(coro_factory):
    async def runner():
        engine = _engine()
        try:
            async with async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)() as db:
                return await coro_factory(db)
        finally:
            await engine.dispose()

    return asyncio.run(runner())


async def _purge_tenant(db, tenant_id):
    params = {"t": tenant_id}
    await db.execute(
        text("DELETE FROM user_tokens WHERE user_id IN (SELECT id FROM users WHERE tenant_id = :t)"), params
    )
    await db.execute(
        text("DELETE FROM user_sessions WHERE user_id IN (SELECT id FROM users WHERE tenant_id = :t)"), params
    )
    await db.execute(text("DELETE FROM audit_logs WHERE tenant_id = :t"), params)
    await db.execute(
        text(
            "DELETE FROM user_facility_memberships WHERE user_id IN (SELECT id FROM users WHERE tenant_id = :t)"
        ),
        params,
    )
    await db.execute(text("DELETE FROM users WHERE tenant_id = :t"), params)
    await db.execute(text("DELETE FROM facilities WHERE tenant_id = :t"), params)
    await db.execute(text("DELETE FROM tenants WHERE id = :t"), params)
    await db.commit()


@pytest.fixture()
def provisioned():
    """A brand-new tenant + facility + admin that has not activated yet."""
    suffix = uuid.uuid4().hex[:8]
    holder = {}

    async def create(db):
        return await provision_admin(
            db,
            tenant_name=f"Test Tenant {suffix}",
            tenant_code=f"TT{suffix}".upper(),
            facility_name=f"Test Facility {suffix}",
            facility_code=f"TF-{suffix}".upper(),
            username=f"p10.admin.{suffix}",
            email=f"p10.admin.{suffix}@example.org",
            full_name="P10 Test Admin",
        )

    result = _run(create)
    holder.update(
        username=result.user.username,
        email=result.user.email,
        token=result.activation_token,
        tenant_id=result.tenant.id,
        user_id=result.user.id,
        facility_id=result.facility.id,
    )
    try:
        yield holder
    finally:
        _run(lambda db: _purge_tenant(db, holder["tenant_id"]))


def test_provisioning_rejects_emails_the_api_could_not_serialize():
    """A reserved domain passes a naive regex but makes /auth/login 500 for that account."""
    from app.core.exceptions import AppError

    async def attempt(db):
        return await provision_admin(
            db, tenant_name="X", tenant_code="XTEST", facility_name="X", facility_code="XTEST-1",
            username="x.reject", email="someone@clinic.test", full_name="X",
        )

    with pytest.raises(AppError):
        _run(attempt)


# ------------------------------------------------------------------ activation


def test_provisioned_admin_has_no_usable_password_until_activated(client, provisioned):
    for guess in (DEMO_PASSWORD, "password", provisioned["username"], ""):
        if guess:
            assert _login(client, provisioned["username"], guess).status_code == 401

    activated = client.post(
        "/api/v1/auth/activate", json={"token": provisioned["token"], "new_password": NEW_PASSWORD}
    )
    assert activated.status_code == 200

    login = _login(client, provisioned["username"], NEW_PASSWORD)
    assert login.status_code == 200
    data = login.json()["data"]
    assert data["user"]["role"]["code"] == "HOSPITAL_ADMIN"
    assert data["user"]["email_verified"] is True
    assert [f["id"] for f in data["facilities"]] == [str(provisioned["facility_id"])]


def test_activation_token_is_single_use(client, provisioned):
    body = {"token": provisioned["token"], "new_password": NEW_PASSWORD}
    assert client.post("/api/v1/auth/activate", json=body).status_code == 200
    again = client.post("/api/v1/auth/activate", json={**body, "new_password": "An0ther!Passw0rd"})
    assert again.status_code == 401
    assert again.json()["error"]["code"] == "INVALID_TOKEN"
    # The first password still stands.
    assert _login(client, provisioned["username"], NEW_PASSWORD).status_code == 200


def test_activation_rejects_garbage_and_wrong_purpose_tokens(client, provisioned):
    junk = client.post("/api/v1/auth/activate", json={"token": "x" * 43, "new_password": NEW_PASSWORD})
    assert junk.status_code == 401
    # An activation token must not work as a reset token.
    wrong = client.post(
        "/api/v1/auth/password-reset/confirm", json={"token": provisioned["token"], "new_password": NEW_PASSWORD}
    )
    assert wrong.status_code == 401


def test_expired_activation_token_is_rejected(client, provisioned):
    async def expire(db):
        await db.execute(
            text("UPDATE user_tokens SET expires_at = now() - interval '1 minute' WHERE user_id = :u"),
            {"u": provisioned["user_id"]},
        )
        await db.commit()

    _run(expire)
    response = client.post(
        "/api/v1/auth/activate", json={"token": provisioned["token"], "new_password": NEW_PASSWORD}
    )
    assert response.status_code == 401


def test_tokens_are_stored_hashed(provisioned):
    async def fetch(db):
        rows = await db.execute(
            text("SELECT token_hash FROM user_tokens WHERE user_id = :u"), {"u": provisioned["user_id"]}
        )
        return [r[0] for r in rows]

    hashes = _run(fetch)
    assert hashes and provisioned["token"] not in hashes
    assert all(len(h) == 64 for h in hashes)


# --------------------------------------------------------------- password reset


def _activate(client, provisioned):
    assert (
        client.post(
            "/api/v1/auth/activate", json={"token": provisioned["token"], "new_password": NEW_PASSWORD}
        ).status_code
        == 200
    )


def test_password_reset_round_trip_revokes_existing_sessions(client, provisioned):
    _activate(client, provisioned)
    assert _login(client, provisioned["username"], NEW_PASSWORD).status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200

    requested = client.post("/api/v1/auth/password-reset/request", json={"identifier": provisioned["email"]})
    assert requested.status_code == 200
    token = requested.json()["data"]["debug_token"]  # local env only
    assert token

    changed = client.post(
        "/api/v1/auth/password-reset/confirm", json={"token": token, "new_password": "Brand!New1Passw0rd"}
    )
    assert changed.status_code == 200

    # The session opened before the reset is dead; old password no longer works.
    assert client.get("/api/v1/auth/me").status_code == 401
    client.cookies.clear()
    assert _login(client, provisioned["username"], NEW_PASSWORD).status_code == 401
    assert _login(client, provisioned["username"], "Brand!New1Passw0rd").status_code == 200

    reuse = client.post(
        "/api/v1/auth/password-reset/confirm", json={"token": token, "new_password": "Third!Passw0rd1"}
    )
    assert reuse.status_code == 401


def test_password_reset_request_does_not_reveal_whether_an_account_exists(client, provisioned):
    _activate(client, provisioned)
    known = client.post("/api/v1/auth/password-reset/request", json={"identifier": provisioned["username"]})
    unknown = client.post("/api/v1/auth/password-reset/request", json={"identifier": "nobody.at.all"})
    assert known.status_code == unknown.status_code == 200
    assert set(known.json()["data"]) == set(unknown.json()["data"])
    assert unknown.json()["data"]["debug_token"] is None


def test_password_reset_ignores_disabled_accounts(client, provisioned):
    _activate(client, provisioned)

    async def disable(db):
        await db.execute(text("UPDATE users SET is_active = false WHERE id = :u"), {"u": provisioned["user_id"]})
        await db.commit()

    _run(disable)
    response = client.post("/api/v1/auth/password-reset/request", json={"identifier": provisioned["username"]})
    assert response.status_code == 200
    assert response.json()["data"]["debug_token"] is None


def test_reset_rejects_weak_password(client, provisioned):
    _activate(client, provisioned)
    token = client.post(
        "/api/v1/auth/password-reset/request", json={"identifier": provisioned["username"]}
    ).json()["data"]["debug_token"]
    assert (
        client.post(
            "/api/v1/auth/password-reset/confirm", json={"token": token, "new_password": "short"}
        ).status_code
        == 422
    )


# ----------------------------------------------------- login states / facilities


def test_disabled_account_gets_a_distinct_error_only_with_the_right_password(client, provisioned):
    _activate(client, provisioned)

    async def disable(db):
        await db.execute(text("UPDATE users SET is_active = false WHERE id = :u"), {"u": provisioned["user_id"]})
        await db.commit()

    _run(disable)
    right = _login(client, provisioned["username"], NEW_PASSWORD)
    assert right.status_code == 401
    assert right.json()["error"]["code"] == "ACCOUNT_DISABLED"
    wrong = _login(client, provisioned["username"], "Wrong!Passw0rd1")
    assert wrong.json()["error"]["code"] != "ACCOUNT_DISABLED"


def test_inactive_tenant_cannot_sign_in(client, provisioned):
    _activate(client, provisioned)

    async def disable(db):
        await db.execute(text("UPDATE tenants SET is_active = false WHERE id = :t"), {"t": provisioned["tenant_id"]})
        await db.commit()

    _run(disable)
    response = _login(client, provisioned["username"], NEW_PASSWORD)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ACCOUNT_DISABLED"


def test_user_without_any_facility_membership_cannot_sign_in(client, provisioned):
    _activate(client, provisioned)

    async def drop(db):
        await db.execute(
            text("DELETE FROM user_facility_memberships WHERE user_id = :u"), {"u": provisioned["user_id"]}
        )
        await db.commit()

    _run(drop)
    response = _login(client, provisioned["username"], NEW_PASSWORD)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NO_FACILITY_ACCESS"


def test_login_to_a_facility_the_user_does_not_belong_to_is_forbidden(client, provisioned):
    _activate(client, provisioned)
    # hospital.admin's facility is a different tenant's facility to this user.
    other = _login(client, HOSPITAL_ADMIN).json()["data"]["facility"]["id"]
    client.cookies.clear()
    response = _login(client, provisioned["username"], NEW_PASSWORD, facility_id=other)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FACILITY_NOT_ASSIGNED"


def test_switch_facility_changes_the_active_facility_for_every_request(client, provisioned):
    _activate(client, provisioned)
    suffix = uuid.uuid4().hex[:6].upper()
    second = {}

    async def add_second_facility(db):
        row = await db.execute(
            text(
                """
                INSERT INTO facilities (id, tenant_id, name, facility_code, timezone, currency, is_active, created_at)
                VALUES (gen_random_uuid(), :t, :n, :c, 'Asia/Kolkata', 'INR', true, now()) RETURNING id
                """
            ),
            {"t": provisioned["tenant_id"], "n": f"Second {suffix}", "c": f"TF2-{suffix}"},
        )
        fid = row.scalar_one()
        await db.execute(
            text(
                "INSERT INTO user_facility_memberships (id, user_id, facility_id, is_default, created_at) "
                "VALUES (gen_random_uuid(), :u, :f, false, now())"
            ),
            {"u": provisioned["user_id"], "f": fid},
        )
        await db.commit()
        return fid

    second["id"] = _run(add_second_facility)

    login = _login(client, provisioned["username"], NEW_PASSWORD).json()["data"]
    assert login["facility"]["id"] == str(provisioned["facility_id"])  # default membership
    assert len(login["facilities"]) == 2

    switched = client.post("/api/v1/auth/switch-facility", json={"facility_id": str(second["id"])})
    assert switched.status_code == 200
    assert switched.json()["data"]["facility"]["id"] == str(second["id"])
    assert client.get("/api/v1/auth/me").json()["data"]["facility"]["id"] == str(second["id"])
    assert client.get("/api/v1/auth/me").json()["data"]["user"]["facility_id"] == str(second["id"])

    # A refresh keeps the switched facility rather than snapping back to home.
    assert client.post("/api/v1/auth/refresh").status_code == 200
    assert client.get("/api/v1/auth/me").json()["data"]["facility"]["id"] == str(second["id"])

    # Removing the membership ends the session's access immediately.
    async def remove(db):
        await db.execute(
            text("DELETE FROM user_facility_memberships WHERE user_id = :u AND facility_id = :f"),
            {"u": provisioned["user_id"], "f": second["id"]},
        )
        await db.commit()

    _run(remove)
    assert client.get("/api/v1/auth/me").status_code == 401

    client.cookies.clear()
    _login(client, provisioned["username"], NEW_PASSWORD)
    foreign = _login(client, HOSPITAL_ADMIN).json()["data"]["facility"]["id"]
    client.cookies.clear()
    _login(client, provisioned["username"], NEW_PASSWORD)
    assert client.post("/api/v1/auth/switch-facility", json={"facility_id": foreign}).status_code == 403


# ------------------------------------------------------------ public enquiries


def _enquiry(**overrides):
    return {
        "organization_name": "Green Valley Clinic",
        "contact_name": "Dr. Test",
        "email": "contact@greenvalley.example",
        "facility_type": "clinic",
        "message": "We would like a demo.",
        **overrides,
    }


def _count_enquiries(email):
    async def count(db):
        return (
            await db.execute(text("SELECT count(*) FROM onboarding_requests WHERE email = :e"), {"e": email})
        ).scalar_one()

    return _run(count)


def _delete_enquiries(email):
    async def delete(db):
        await db.execute(text("DELETE FROM onboarding_requests WHERE email = :e"), {"e": email})
        await db.execute(text("DELETE FROM audit_logs WHERE action = 'onboarding.request_received'"))
        await db.commit()

    _run(delete)


def test_public_onboarding_request_is_stored_without_authentication(client):
    email = f"p10.{uuid.uuid4().hex[:8]}@greenvalley.example"
    try:
        response = client.post("/api/v1/public/onboarding-requests", json=_enquiry(email=email))
        assert response.status_code == 200
        assert response.json()["data"] == {"received": True}
        assert _count_enquiries(email) == 1
    finally:
        _delete_enquiries(email)


def test_public_onboarding_honeypot_stores_nothing(client):
    email = f"bot.{uuid.uuid4().hex[:8]}@spam.example"
    response = client.post("/api/v1/public/onboarding-requests", json=_enquiry(email=email, website="http://x"))
    assert response.status_code == 200
    assert _count_enquiries(email) == 0


def test_public_onboarding_validates_input(client):
    assert client.post("/api/v1/public/onboarding-requests", json=_enquiry(email="not-an-email")).status_code == 422
    assert client.post("/api/v1/public/onboarding-requests", json=_enquiry(organization_name="")).status_code == 422
    assert client.post("/api/v1/public/onboarding-requests", json=_enquiry(message="x" * 2001)).status_code == 422


def test_public_endpoint_exposes_no_listing(client):
    assert client.get("/api/v1/public/onboarding-requests").status_code in (404, 405)
