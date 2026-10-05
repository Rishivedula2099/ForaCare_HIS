"""Lab module security tests (P6-B09).

Five scenarios against the real API, each proven with an HTTP status code
and error code from a real request - no test asserts on `role == "..."` or
calls a service function directly. Overlaps intentionally with
`test_lab_authorization.py` (P6-B07) in places - that file is about *who*
may act, this one is about the specific *attack/misuse* scenarios named in
P6-B09, several of which (unauthorized approval, cross-facility access) are
the same underlying guard exercised from a different angle.
"""
import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

DEMO_PASSWORD = "Demo@123"

HOSPITAL_ADMIN = "hospital.admin"
LAB_TECH = "lab.tech"
LAB_APPROVER = "lab.approver"

TENANT_ID = "11111111-1111-1111-1111-111111111111"
FACILITY_METRO_ID = "22222222-2222-2222-2222-222222222203"
FACILITY_MAIN_ID = "22222222-2222-2222-2222-222222222201"
SEEDED_PATIENT_ID = "44444444-4444-4444-4444-444444444401"


def _login(client, username: str, password: str = DEMO_PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _create_test_and_parameter(client) -> tuple[str, str]:
    suffix = uuid.uuid4().hex[:8].upper()
    test_response = client.post(
        "/api/v1/lab/tests",
        json={
            "test_code": f"SEC{suffix}",
            "name": f"Security Test {suffix}",
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
    return test_id, parameter_response.json()["data"]["id"]


class _LabOrderSeed:
    """Same raw-SQL seeding approach as `test_lab_authorization.py` - there
    is no public "place an order" endpoint, so a test needing an order
    already past BILLED has to insert it directly."""

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
                    "order_number": f"SEC-{uuid.uuid4().hex[:10]}",
                    "status": status,
                    "now": now,
                },
            )
        self.order_ids.append(order_id)
        return order_id

    async def create_result(
        self, *, lab_order_id: str, parameter_id: str, status: str = "VERIFIED", value: str = "5.0"
    ) -> str:
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
                        (:id, :tenant_id, :facility_id, :lab_order_id, :parameter_id, :value, 'mg/dL',
                         'NORMAL', :status, 1, :now, :now, :now)
                    """
                ),
                {
                    "id": result_id,
                    "tenant_id": TENANT_ID,
                    "facility_id": FACILITY_METRO_ID,
                    "lab_order_id": lab_order_id,
                    "parameter_id": parameter_id,
                    "value": value,
                    "status": status,
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
# 1: unauthorized result modification
# ---------------------------------------------------------------------------


def test_user_without_enter_results_cannot_post_results(client, lab_order_seed):
    _login(client, LAB_APPROVER)
    test_id, parameter_id = _create_test_and_parameter(client)
    order_id = asyncio.run(lab_order_seed.create_order(test_id=test_id, status="PROCESSING"))

    # hospital.admin holds `lab.view` but not `lab.enter_results`.
    _login(client, HOSPITAL_ADMIN)
    me = client.get("/api/v1/auth/me").json()["data"]["user"]
    assert "lab.enter_results" not in me["permissions"]

    response = client.post(
        f"/api/v1/lab/orders/{order_id}/results",
        json={"items": [{"parameter_id": parameter_id, "value": "1.0"}]},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_user_without_approve_reports_cannot_amend_a_result(client, lab_order_seed):
    _login(client, LAB_APPROVER)
    test_id, parameter_id = _create_test_and_parameter(client)
    order_id = asyncio.run(lab_order_seed.create_order(test_id=test_id, status="APPROVED"))
    result_id = asyncio.run(
        lab_order_seed.create_result(lab_order_id=order_id, parameter_id=parameter_id, status="APPROVED")
    )

    # lab.tech can enter/collect results but holds no approval authority,
    # so amending an already-approved result must also be out of reach.
    _login(client, LAB_TECH)
    me = client.get("/api/v1/auth/me").json()["data"]["user"]
    assert "lab.approve_reports" not in me["permissions"]

    response = client.patch(
        f"/api/v1/lab/results/{result_id}/amend",
        json={"value": "999.0", "reason": "unauthorized attempt"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# 2: unauthorized approval
# ---------------------------------------------------------------------------


def test_unauthorized_user_cannot_approve_results(client, lab_order_seed):
    _login(client, LAB_APPROVER)
    test_id, parameter_id = _create_test_and_parameter(client)
    order_id = asyncio.run(lab_order_seed.create_order(test_id=test_id, status="PENDING_APPROVAL"))
    asyncio.run(lab_order_seed.create_result(lab_order_id=order_id, parameter_id=parameter_id))

    _login(client, LAB_TECH)
    response = client.post(f"/api/v1/lab/orders/{order_id}/approve", json={"remarks": None})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"

    # The order must be untouched - still PENDING_APPROVAL, not APPROVED.
    _login(client, LAB_APPROVER)
    order = client.get(f"/api/v1/lab/orders/{order_id}").json()["data"]
    assert order["status"] == "PENDING_APPROVAL"


# ---------------------------------------------------------------------------
# 3: invalid state transition
# ---------------------------------------------------------------------------


def test_cannot_approve_an_order_that_is_not_pending_approval(client, lab_order_seed):
    _login(client, LAB_APPROVER)
    test_id, parameter_id = _create_test_and_parameter(client)
    # ACCESSIONED is nowhere near PENDING_APPROVAL in the state machine.
    order_id = asyncio.run(lab_order_seed.create_order(test_id=test_id, status="ACCESSIONED"))

    response = client.post(f"/api/v1/lab/orders/{order_id}/approve", json={"remarks": None})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_TRANSITION"


def test_cannot_jump_a_lab_order_directly_to_finalized(client, lab_order_seed):
    _login(client, LAB_APPROVER)
    test_id, _parameter_id = _create_test_and_parameter(client)
    order_id = asyncio.run(lab_order_seed.create_order(test_id=test_id, status="ORDERED"))

    response = client.patch(f"/api/v1/lab/orders/{order_id}/status", json={"status": "FINALIZED"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_TRANSITION"

    order = client.get(f"/api/v1/lab/orders/{order_id}").json()["data"]
    assert order["status"] == "ORDERED"


def test_cannot_enter_results_on_an_order_not_yet_processing(client, lab_order_seed):
    _login(client, LAB_APPROVER)
    test_id, parameter_id = _create_test_and_parameter(client)
    order_id = asyncio.run(lab_order_seed.create_order(test_id=test_id, status="BILLED"))

    # LAB_TECH (not LAB_APPROVER) genuinely holds `lab.enter_results`, so
    # this isolates the business-rule check in `enter_results` from the
    # route's permission dependency - a 403 here would mean the wrong
    # layer rejected the request.
    _login(client, LAB_TECH)
    response = client.post(
        f"/api/v1/lab/orders/{order_id}/results",
        json={"items": [{"parameter_id": parameter_id, "value": "1.0"}]},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_TRANSITION"


# ---------------------------------------------------------------------------
# 4: cross-facility access
# ---------------------------------------------------------------------------


def test_cross_facility_user_cannot_read_order_results_or_history(client, lab_order_seed):
    _login(client, LAB_APPROVER)
    test_id, parameter_id = _create_test_and_parameter(client)
    order_id = asyncio.run(lab_order_seed.create_order(test_id=test_id, status="PENDING_APPROVAL"))
    asyncio.run(lab_order_seed.create_result(lab_order_id=order_id, parameter_id=parameter_id))

    # hospital.admin is FACILITY_MAIN; the order above was seeded at
    # FACILITY_METRO_ID - every lab resource is scoped by its own
    # `facility_id`, not by patient or by who's asking, so `lab.view` alone
    # (which hospital.admin does hold) must not be enough to cross that
    # boundary on any of these three endpoints.
    _login(client, HOSPITAL_ADMIN)
    me = client.get("/api/v1/auth/me").json()["data"]["user"]
    assert me["facility_id"] == FACILITY_MAIN_ID != FACILITY_METRO_ID
    assert "lab.view" in me["permissions"]

    order_response = client.get(f"/api/v1/lab/orders/{order_id}")
    assert order_response.status_code == 404
    assert order_response.json()["error"]["code"] == "NOT_FOUND"

    results_response = client.get(f"/api/v1/lab/orders/{order_id}/results")
    assert results_response.status_code == 404

    history_response = client.get(f"/api/v1/lab/orders/{order_id}/status-history")
    assert history_response.status_code == 404


@pytest.fixture
def hospital_admin_with_approve_reports(client):
    """Isolates the facility check from the permission check: grants
    HOSPITAL_ADMIN (seeded at FACILITY_MAIN) `lab.approve_reports` so a
    cross-facility approval attempt can only be rejected by
    `ensure_same_facility`, not by a missing permission - always revoked
    afterward."""
    setup_engine = create_async_engine(get_settings().database_url, poolclass=NullPool)

    async def grant():
        async with setup_engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT r.id, p.id FROM roles r, permissions p
                    WHERE r.code = 'HOSPITAL_ADMIN' AND p.code = 'lab.approve_reports'
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
                    WHERE role_id = (SELECT id FROM roles WHERE code = 'HOSPITAL_ADMIN')
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


def test_cross_facility_approval_is_blocked_even_with_the_right_permission(
    client, lab_order_seed, hospital_admin_with_approve_reports
):
    _login(client, LAB_APPROVER)
    test_id, parameter_id = _create_test_and_parameter(client)
    order_id = asyncio.run(lab_order_seed.create_order(test_id=test_id, status="PENDING_APPROVAL"))
    asyncio.run(lab_order_seed.create_result(lab_order_id=order_id, parameter_id=parameter_id))

    _login(client, HOSPITAL_ADMIN)
    me = client.get("/api/v1/auth/me").json()["data"]["user"]
    assert "lab.approve_reports" in me["permissions"]
    assert me["facility_id"] != FACILITY_METRO_ID

    response = client.post(f"/api/v1/lab/orders/{order_id}/approve", json={"remarks": None})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# 5: amendment authorization
# ---------------------------------------------------------------------------


def test_amendment_requires_order_to_be_approved_or_finalized(client, lab_order_seed):
    _login(client, LAB_APPROVER)
    test_id, parameter_id = _create_test_and_parameter(client)
    # RESULT_ENTERED - not yet approved - amend_result must refuse even
    # though the caller genuinely holds `lab.approve_reports`.
    order_id = asyncio.run(lab_order_seed.create_order(test_id=test_id, status="RESULT_ENTERED"))
    result_id = asyncio.run(
        lab_order_seed.create_result(lab_order_id=order_id, parameter_id=parameter_id, status="ENTERED")
    )

    response = client.patch(
        f"/api/v1/lab/results/{result_id}/amend",
        json={"value": "42.0", "reason": "too early"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_TRANSITION"


def test_amendment_requires_a_reason(client, lab_order_seed):
    _login(client, LAB_APPROVER)
    test_id, parameter_id = _create_test_and_parameter(client)
    order_id = asyncio.run(lab_order_seed.create_order(test_id=test_id, status="APPROVED"))
    result_id = asyncio.run(
        lab_order_seed.create_result(lab_order_id=order_id, parameter_id=parameter_id, status="APPROVED")
    )

    response = client.patch(f"/api/v1/lab/results/{result_id}/amend", json={"value": "42.0", "reason": ""})
    assert response.status_code == 422


def test_authorized_amendment_succeeds_and_bumps_version(client, lab_order_seed):
    _login(client, LAB_APPROVER)
    test_id, parameter_id = _create_test_and_parameter(client)
    order_id = asyncio.run(lab_order_seed.create_order(test_id=test_id, status="APPROVED"))
    result_id = asyncio.run(
        lab_order_seed.create_result(lab_order_id=order_id, parameter_id=parameter_id, status="APPROVED")
    )

    response = client.patch(
        f"/api/v1/lab/results/{result_id}/amend",
        json={"value": "42.0", "reason": "transcription error"},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["value"] == "42.0"
    assert data["status"] == "AMENDED"
    assert data["current_version"] == 2

    versions = client.get(f"/api/v1/lab/results/{result_id}/versions").json()["data"]
    assert len(versions) == 1
    assert versions[0]["change_reason"] == "transcription error"
