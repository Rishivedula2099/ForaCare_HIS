"""Billing module authorization (S5-B01 permission-centric fix).

Covers the required authorization model end-to-end against the real API:
`billing.view` gates module access, separately from the per-action
`billing.invoice.create` / `billing.payment.create` / `billing.refund.create`
permissions - module access is not full billing authority. No test here
asserts on `role == "..."`; every assertion is either an HTTP status code
from a real request or a permission-set check against `/auth/me`.
"""
import asyncio
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.security import hash_password

DEMO_PASSWORD = "Demo@123"

HOSPITAL_ADMIN = "hospital.admin"
BILLING_CASHIER = "billing.cashier"
# Same tenant as HOSPITAL_ADMIN/BILLING_CASHIER, but a different facility
# (FACILITY_METRO_ID rather than FACILITY_MAIN_ID) - used for the
# cross-facility isolation test.
LAB_TECH = "lab.tech"

# A seeded demo patient in the same tenant/facility as HOSPITAL_ADMIN and
# BILLING_CASHIER (backend/migrations/versions/..._seed_demo_patients.py).
SEEDED_PATIENT_ID = "44444444-4444-4444-4444-444444444401"

TENANT_ID = "11111111-1111-1111-1111-111111111111"
FACILITY_MAIN_ID = "22222222-2222-2222-2222-222222222201"


def _login(client, username: str, password: str = DEMO_PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _create_minimal_invoice(client, *, patient_id: str = SEEDED_PATIENT_ID) -> str:
    response = client.post(
        "/api/v1/billing/invoices",
        json={
            "patient_id": patient_id,
            "items": [
                {"item_type": "CUSTOM", "description": "Test charge", "quantity": 1, "unit_price": 10.0}
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["id"]


def _collect_minimal_payment(client, invoice_id: str) -> str:
    response = client.post(
        f"/api/v1/billing/invoices/{invoice_id}/payments",
        json={"amount": 10.0, "payment_mode": "CASH"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]["id"]


# ---------------------------------------------------------------------------
# 1 & 2: module access is gated on `billing.view`, not a hard-coded role
# ---------------------------------------------------------------------------


def test_hospital_admin_has_billing_view_and_can_open_the_module(client):
    _login(client, HOSPITAL_ADMIN)

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert "billing.view" in me.json()["data"]["user"]["permissions"]

    assert client.get("/api/v1/billing/services").status_code == 200
    assert client.get("/api/v1/billing/invoices").status_code == 200
    assert client.get("/api/v1/billing/packages").status_code == 200
    assert client.get("/api/v1/billing/deposits").status_code == 200


def test_billing_cashier_has_billing_view_and_can_open_the_module(client):
    _login(client, BILLING_CASHIER)

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert "billing.view" in me.json()["data"]["user"]["permissions"]

    assert client.get("/api/v1/billing/services").status_code == 200
    assert client.get("/api/v1/billing/invoices").status_code == 200
    assert client.get("/api/v1/billing/packages").status_code == 200
    assert client.get("/api/v1/billing/deposits").status_code == 200


def test_hospital_admin_and_billing_cashier_can_create_invoices_and_collect_payments(client):
    # Module access != full billing authority in the other direction too:
    # both roles are supposed to have these two action permissions, so
    # confirm neither is accidentally missing them.
    for username in (HOSPITAL_ADMIN, BILLING_CASHIER):
        _login(client, username)
        invoice_id = _create_minimal_invoice(client)
        payment = client.post(
            f"/api/v1/billing/invoices/{invoice_id}/payments",
            json={"amount": 10.0, "payment_mode": "CASH"},
        )
        assert payment.status_code == 200, f"{username}: {payment.text}"


# ---------------------------------------------------------------------------
# 3 & 4: refund authority is a distinct permission, withheld only from the cashier
# ---------------------------------------------------------------------------


def test_billing_cashier_lacks_refund_create_and_refund_api_returns_403(client):
    _login(client, HOSPITAL_ADMIN)
    invoice_id = _create_minimal_invoice(client)
    payment_id = _collect_minimal_payment(client, invoice_id)

    _login(client, BILLING_CASHIER)
    me = client.get("/api/v1/auth/me").json()["data"]["user"]
    assert "billing.refund.create" not in me["permissions"]

    refund = client.post(
        "/api/v1/billing/refunds",
        json={"payment_id": payment_id, "amount": 10.0, "reason": "test", "refund_mode": "CASH"},
    )
    assert refund.status_code == 403


def test_hospital_admin_has_refund_create_and_refund_api_is_accessible(client):
    _login(client, HOSPITAL_ADMIN)
    invoice_id = _create_minimal_invoice(client)
    payment_id = _collect_minimal_payment(client, invoice_id)

    me = client.get("/api/v1/auth/me").json()["data"]["user"]
    assert "billing.refund.create" in me["permissions"]

    refund = client.post(
        "/api/v1/billing/refunds",
        json={"payment_id": payment_id, "amount": 10.0, "reason": "test", "refund_mode": "CASH"},
    )
    assert refund.status_code == 200, refund.text


# ---------------------------------------------------------------------------
# 5: a role without `billing.view` stays locked out of the module
# ---------------------------------------------------------------------------


@pytest.fixture
def no_billing_role_user(client):
    """A throwaway role with zero permissions and a user assigned to it -
    every seeded demo role now holds `billing.view` (Billing was
    deliberately opened to every role except SUPER_ADMIN), so proving the
    *permission* (not a role name) gates the module needs a role that
    genuinely lacks it. Created and torn down per-test rather than
    borrowing/mutating a real seeded role, since this test suite runs
    against a real, shared, non-transactional database.
    """
    role_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    unique_suffix = uuid.uuid4().hex[:8]
    role_code = f"TEST_NO_BILLING_{unique_suffix}"
    username = f"test.no.billing.{unique_suffix}"
    # `roles.numeric_code` is unique - stay far outside the seeded 1-9 range
    # and vary it (a fixed 9000 would collide across repeated test runs).
    numeric_code = 900_000 + int(unique_suffix, 16) % 90_000

    # A dedicated, unpooled engine for this one-off setup/teardown - not the
    # app's shared `engine` (see app/core/database.py), whose pooled
    # asyncpg connections are bound to the TestClient portal's event loop;
    # mixing that pool with a fresh `asyncio.run()` loop here raises
    # "attached to a different loop" on Windows (see conftest.py's note on
    # asyncpg + ProactorEventLoop).
    setup_engine = create_async_engine(get_settings().database_url, poolclass=NullPool)

    async def setup():
        async with setup_engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO roles (id, numeric_code, code, name, is_system, created_at, updated_at)
                    VALUES (:id, :numeric_code, :code, :name, false, now(), now())
                    """
                ),
                {"id": role_id, "numeric_code": numeric_code, "code": role_code, "name": "Test - No Billing Access"},
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO users
                        (id, tenant_id, facility_id, username, email, password_hash, full_name, role_id,
                         is_active, created_at, updated_at)
                    VALUES
                        (:id, :tenant_id, :facility_id, :username, :email, :password_hash, :full_name, :role_id,
                         true, now(), now())
                    """
                ),
                {
                    "id": user_id,
                    "tenant_id": TENANT_ID,
                    "facility_id": FACILITY_MAIN_ID,
                    "username": username,
                    "email": f"{username}@foracare-his.com",
                    "password_hash": hash_password(DEMO_PASSWORD),
                    "full_name": "Test No Billing Access",
                    "role_id": role_id,
                },
            )

    async def teardown():
        async with setup_engine.begin() as conn:
            # Logging in creates a user_sessions row, and the denied
            # `/billing/services` request writes an audit_logs row (see
            # require_billing_permission in app/modules/billing/security.py)
            # - both reference this user and must go before it's deleted.
            await conn.execute(text("DELETE FROM user_sessions WHERE user_id = :id"), {"id": user_id})
            await conn.execute(text("DELETE FROM audit_logs WHERE actor_user_id = :id"), {"id": user_id})
            await conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": user_id})
            await conn.execute(text("DELETE FROM roles WHERE id = :id"), {"id": role_id})
        await setup_engine.dispose()

    asyncio.run(setup())
    try:
        yield username
    finally:
        asyncio.run(teardown())


def test_user_without_billing_view_is_forbidden(client, no_billing_role_user):
    login = _login(client, no_billing_role_user)
    assert login.status_code == 200

    me = client.get("/api/v1/auth/me").json()["data"]["user"]
    assert "billing.view" not in me["permissions"]

    response = client.get("/api/v1/billing/services")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# 6: facility isolation - billing.view does not cross facility boundaries
# ---------------------------------------------------------------------------


def test_user_from_another_facility_cannot_access_the_invoice(client):
    _login(client, HOSPITAL_ADMIN)
    invoice_id = _create_minimal_invoice(client)

    # lab.tech is in the same tenant but a different facility
    # (FACILITY_METRO_ID) - and, per the "open to every role except
    # SUPER_ADMIN" decision, does hold `billing.view`. The permission alone
    # must not be enough to see another facility's invoice.
    _login(client, LAB_TECH)
    me = client.get("/api/v1/auth/me").json()["data"]["user"]
    assert "billing.view" in me["permissions"]
    assert me["facility_id"] != FACILITY_MAIN_ID

    response = client.get(f"/api/v1/billing/invoices/{invoice_id}")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# 7: the API enforces this independently of any frontend guard - every
# assertion above already goes straight through the HTTP client to the
# real FastAPI dependency chain (no test here calls a service function or
# frontend hook directly), so a direct curl/Postman request follows the
# exact same rules a browser would.
# ---------------------------------------------------------------------------
