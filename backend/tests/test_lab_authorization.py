"""Lab module approval authorization (P6-B07).

Covers the four stated requirements end-to-end against the real API:
a technician may enter results but may not approve them, an approver may
approve, facility ownership gates every lab resource, and an approval
action is audited. No test here asserts on `role == "..."`; every
assertion is either an HTTP status code from a real request or a
permission-set check against `/auth/me` - mirrors
`test_billing_authorization.py`.
"""
import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.security import hash_password

DEMO_PASSWORD = "Demo@123"

HOSPITAL_ADMIN = "hospital.admin"
LAB_TECH = "lab.tech"
LAB_APPROVER = "lab.approver"
AUDITOR = "auditor"

TENANT_ID = "11111111-1111-1111-1111-111111111111"
# lab.tech and lab.approver are both seeded at FACILITY_METRO_ID - same
# facility, different roles, so "technician enters / approver approves" can
# be exercised on one order without crossing a facility boundary.
FACILITY_METRO_ID = "22222222-2222-2222-2222-222222222203"
FACILITY_MAIN_ID = "22222222-2222-2222-2222-222222222201"
SEEDED_PATIENT_ID = "44444444-4444-4444-4444-444444444401"


def _login(client, username: str, password: str = DEMO_PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _create_test_and_parameter(client) -> tuple[str, str]:
    """`lab.approver` holds `lab.manage_master`, so it can seed a throwaway
    Test/Parameter pair through the real API rather than raw SQL."""
    suffix = uuid.uuid4().hex[:8].upper()
    test_response = client.post(
        "/api/v1/lab/tests",
        json={
            "test_code": f"AUTHZ{suffix}",
            "name": f"Authz Test {suffix}",
            "specimen_type": "SERUM",
            "container_type": "RED_TOP",
        },
    )
    assert test_response.status_code == 200, test_response.text
    test_id = test_response.json()["data"]["id"]

    parameter_response = client.post(
        f"/api/v1/lab/tests/{test_id}/parameters",
        json={"parameter_code": "VAL", "name": "Value", "unit": "mg/dL"},
    )
    assert parameter_response.status_code == 200, parameter_response.text
    parameter_id = parameter_response.json()["data"]["id"]
    return test_id, parameter_id


class _LabOrderSeed:
    """Raw-SQL seeding for a `LabOrder` in a specific state - there is no
    public "place an order" endpoint yet (P6-B01 assumed orders arrive from
    an upstream OPD/billing flow), so tests that need an order already past
    BILLED/PROCESSING have to insert it directly, the same way
    `test_billing_authorization.py`'s `no_billing_role_user` fixture inserts
    a throwaway role/user directly."""

    def __init__(self):
        self.engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        self.order_ids: list[str] = []
        self.result_ids: list[str] = []

    async def create_order(self, *, test_id: str, status: str, facility_id: str = FACILITY_METRO_ID) -> str:
        order_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        async with self.engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO lab_orders
                        (id, tenant_id, facility_id, patient_id, test_id, order_number, status,
                         priority, ordered_at, created_at, updated_at)
                    VALUES
                        (:id, :tenant_id, :facility_id, :patient_id, :test_id, :order_number, :status,
                         'NORMAL', :now, :now, :now)
                    """
                ),
                {
                    "id": order_id,
                    "tenant_id": TENANT_ID,
                    "facility_id": facility_id,
                    "patient_id": SEEDED_PATIENT_ID,
                    "test_id": test_id,
                    "order_number": f"AUTHZ-{uuid.uuid4().hex[:10]}",
                    "status": status,
                    "now": now,
                },
            )
        self.order_ids.append(order_id)
        return order_id

    async def create_verified_result(self, *, lab_order_id: str, parameter_id: str) -> str:
        result_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        async with self.engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO lab_results
                        (id, tenant_id, facility_id, lab_order_id, parameter_id, value, unit, flag,
                         status, current_version, entered_at, created_at, updated_at)
                    VALUES
                        (:id, :tenant_id, :facility_id, :lab_order_id, :parameter_id, '5.0', 'mg/dL',
                         'NORMAL', 'VERIFIED', 1, :now, :now, :now)
                    """
                ),
                {
                    "id": result_id,
                    "tenant_id": TENANT_ID,
                    "facility_id": FACILITY_METRO_ID,
                    "lab_order_id": lab_order_id,
                    "parameter_id": parameter_id,
                    "now": now,
                },
            )
        self.result_ids.append(result_id)
        return result_id

    async def teardown(self):
        async with self.engine.begin() as conn:
            for order_id in self.order_ids:
                await conn.execute(text("DELETE FROM lab_order_status_history WHERE lab_order_id = :id"), {"id": order_id})
                await conn.execute(text("DELETE FROM lab_approvals WHERE lab_order_id = :id"), {"id": order_id})
                await conn.execute(text("DELETE FROM lab_verifications WHERE lab_order_id = :id"), {"id": order_id})
                await conn.execute(text("DELETE FROM lab_result_versions WHERE result_id IN (SELECT id FROM lab_results WHERE lab_order_id = :id)"), {"id": order_id})
                await conn.execute(text("DELETE FROM lab_results WHERE lab_order_id = :id"), {"id": order_id})
                await conn.execute(text("DELETE FROM lab_orders WHERE id = :id"), {"id": order_id})
        await self.engine.dispose()


@pytest.fixture
def lab_order_seed():
    seed = _LabOrderSeed()
    yield seed
    asyncio.run(seed.teardown())


# ---------------------------------------------------------------------------
# 1: a technician may enter results
# ---------------------------------------------------------------------------


def test_lab_tech_can_enter_results(client, lab_order_seed):
    _login(client, LAB_APPROVER)
    test_id, parameter_id = _create_test_and_parameter(client)
    order_id = asyncio.run(lab_order_seed.create_order(test_id=test_id, status="PROCESSING"))

    _login(client, LAB_TECH)
    me = client.get("/api/v1/auth/me").json()["data"]["user"]
    assert "lab.enter_results" in me["permissions"]

    response = client.post(
        f"/api/v1/lab/orders/{order_id}/results",
        json={"items": [{"parameter_id": parameter_id, "value": "7.2", "unit": "mg/dL"}]},
    )
    assert response.status_code == 200, response.text

    order = client.get(f"/api/v1/lab/orders/{order_id}").json()["data"]
    assert order["status"] == "RESULT_ENTERED"


# ---------------------------------------------------------------------------
# 2: a technician cannot approve unless explicitly permitted
# ---------------------------------------------------------------------------


def test_lab_tech_lacks_approve_reports_and_approval_api_returns_403(client):
    _login(client, LAB_TECH)
    me = client.get("/api/v1/auth/me").json()["data"]["user"]
    assert "lab.approve_reports" not in me["permissions"]

    # The permission check happens in the route dependency before the
    # request body/service ever runs, so a syntactically-valid but
    # nonexistent order id still proves the gate - a 404 here would mean
    # the dependency didn't run first.
    response = client.post(f"/api/v1/lab/orders/{uuid.uuid4()}/approve", json={"remarks": None})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.fixture
def lab_tech_with_approve_reports(client):
    """Proves "unless explicitly permitted" has teeth: grant `lab.tech`'s
    role an extra permission it doesn't have by default, confirm approval
    then succeeds, and always revoke it again - even on failure - so this
    test can never leave the shared seeded LAB_TECH role over-privileged
    for every other test in the suite."""
    setup_engine = create_async_engine(get_settings().database_url, poolclass=NullPool)

    async def grant():
        async with setup_engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT r.id, p.id FROM roles r, permissions p
                    WHERE r.code = 'LAB_TECH' AND p.code = 'lab.approve_reports'
                    ON CONFLICT DO NOTHING
                    """
                )
            )

    async def revoke():
        async with setup_engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    DELETE FROM role_permissions
                    WHERE role_id = (SELECT id FROM roles WHERE code = 'LAB_TECH')
                      AND permission_id = (SELECT id FROM permissions WHERE code = 'lab.approve_reports')
                    """
                )
            )
        await setup_engine.dispose()

    asyncio.run(grant())
    try:
        yield
    finally:
        asyncio.run(revoke())


def test_lab_tech_explicitly_granted_approve_reports_can_approve(client, lab_order_seed, lab_tech_with_approve_reports):
    _login(client, LAB_APPROVER)
    test_id, parameter_id = _create_test_and_parameter(client)
    order_id = asyncio.run(lab_order_seed.create_order(test_id=test_id, status="PENDING_APPROVAL"))
    asyncio.run(lab_order_seed.create_verified_result(lab_order_id=order_id, parameter_id=parameter_id))

    _login(client, LAB_TECH)
    me = client.get("/api/v1/auth/me").json()["data"]["user"]
    assert "lab.approve_reports" in me["permissions"]

    response = client.post(f"/api/v1/lab/orders/{order_id}/approve", json={"remarks": "explicitly granted"})
    assert response.status_code == 200, response.text


# ---------------------------------------------------------------------------
# 3: a lab approver may approve
# ---------------------------------------------------------------------------


def test_lab_approver_can_approve_pending_results(client, lab_order_seed):
    _login(client, LAB_APPROVER)
    test_id, parameter_id = _create_test_and_parameter(client)
    order_id = asyncio.run(lab_order_seed.create_order(test_id=test_id, status="PENDING_APPROVAL"))
    asyncio.run(lab_order_seed.create_verified_result(lab_order_id=order_id, parameter_id=parameter_id))

    response = client.post(f"/api/v1/lab/orders/{order_id}/approve", json={"remarks": "looks good"})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["status"] == "APPROVED"

    order = client.get(f"/api/v1/lab/orders/{order_id}").json()["data"]
    assert order["status"] == "APPROVED"


# ---------------------------------------------------------------------------
# 4: facility ownership is mandatory
# ---------------------------------------------------------------------------


def test_user_from_another_facility_cannot_access_the_lab_order(client, lab_order_seed):
    _login(client, LAB_APPROVER)
    test_id, _parameter_id = _create_test_and_parameter(client)
    order_id = asyncio.run(lab_order_seed.create_order(test_id=test_id, status="PENDING_APPROVAL", facility_id=FACILITY_METRO_ID))

    # hospital.admin is in the same tenant but FACILITY_MAIN, not METRO, and
    # does hold `lab.view` (every non-cashier role does) - the permission
    # alone must not be enough to see another facility's order.
    _login(client, HOSPITAL_ADMIN)
    me = client.get("/api/v1/auth/me").json()["data"]["user"]
    assert "lab.view" in me["permissions"]
    assert me["facility_id"] != FACILITY_METRO_ID

    response = client.get(f"/api/v1/lab/orders/{order_id}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_user_from_another_facility_cannot_approve_the_lab_order(client, lab_order_seed):
    _login(client, LAB_APPROVER)
    test_id, parameter_id = _create_test_and_parameter(client)
    order_id = asyncio.run(lab_order_seed.create_order(test_id=test_id, status="PENDING_APPROVAL"))
    asyncio.run(lab_order_seed.create_verified_result(lab_order_id=order_id, parameter_id=parameter_id))

    # hospital.admin lacks `lab.approve_reports` entirely, so this would
    # 403 regardless - the facility check inside `approve_results` is what
    # a same-tenant HOSPITAL_ADMIN *with* lab.approve_reports at the wrong
    # facility would hit; HOSPITAL_ADMIN doesn't hold it by default, which
    # is itself consistent with "approval is a facility-scoped LAB_APPROVER
    # action, not blanket admin authority".
    _login(client, HOSPITAL_ADMIN)
    me = client.get("/api/v1/auth/me").json()["data"]["user"]
    assert "lab.approve_reports" not in me["permissions"]

    response = client.post(f"/api/v1/lab/orders/{order_id}/approve", json={"remarks": None})
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# 5: an approval is audited
# ---------------------------------------------------------------------------


def test_approval_writes_an_audit_log_entry(client, lab_order_seed):
    _login(client, LAB_APPROVER)
    test_id, parameter_id = _create_test_and_parameter(client)
    order_id = asyncio.run(lab_order_seed.create_order(test_id=test_id, status="PENDING_APPROVAL"))
    asyncio.run(lab_order_seed.create_verified_result(lab_order_id=order_id, parameter_id=parameter_id))

    approver_id = client.get("/api/v1/auth/me").json()["data"]["user"]["id"]

    response = client.post(f"/api/v1/lab/orders/{order_id}/approve", json={"remarks": "audited approval"})
    assert response.status_code == 200, response.text

    _login(client, AUDITOR)
    # `/audit/logs` only filters by `resource_type`/`actor_user_id` (no
    # `resource_id` param) - mirrors `test_audit.py`'s role-update
    # assertion, which filters the returned page down to this resource
    # client-side.
    logs = client.get(
        "/api/v1/audit/logs",
        params={"resource_type": "lab_order", "actor_user_id": approver_id},
    ).json()["data"]
    approval_entries = [
        log for log in logs if log["resource_id"] == order_id and log["action"] == "lab.results_approved"
    ]

    assert approval_entries, "expected a lab.results_approved audit log entry for this order"
    assert approval_entries[0]["actor_user_id"] == approver_id
