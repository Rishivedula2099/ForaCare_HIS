"""P3-B07 security tests for the OPD module: token state-machine
enforcement, concurrency protection, consultation authorization, and QR
check-in security (invalid/expired/cross-facility). Mirrors the existing
test_patients.py/test_multitenancy.py conventions - demo seed data over a
shared DB, no per-test rollback.
"""

import concurrent.futures
import subprocess
import sys

DEMO_PASSWORD = "Demo@123"

RECEPTIONIST = "receptionist"
DOCTOR = "dr.priya"
SUNRISE_ADMIN = "sunrise.admin"

SEEDED_PATIENT_ID = "44444444-4444-4444-4444-444444444401"
DEPT_GENMED_ID = "55555555-5555-5555-5555-555555555501"
DEPT_CARDIO_ID = "55555555-5555-5555-5555-555555555502"
DOCTOR_GENMED_ID = "66666666-6666-6666-6666-666666666601"  # not linked to any login
DOCTOR_CARDIO_ID = "66666666-6666-6666-6666-666666666602"  # linked to dr.priya


def _login(client, username: str, password: str = DEMO_PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _register_encounter(client, *, doctor_id=DOCTOR_GENMED_ID, department_id=DEPT_GENMED_ID):
    response = client.post(
        "/api/v1/opd/encounters",
        json={
            "patient_id": SEEDED_PATIENT_ID,
            "department_id": department_id,
            "doctor_id": doctor_id,
            "visit_type": "WALK_IN",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _run_db_script(body: str) -> None:
    """Runs a snippet against the real DB in a separate process rather than
    on this test's own event loop: the `client` fixture keeps its asyncpg
    connections bound to its own dedicated anyio portal/loop (see
    conftest.py's note on Windows' ProactorEventLoop), so a second asyncio
    DB session opened from pytest's loop in the same test crashes with
    "attached to a different loop"."""
    import pathlib

    backend_root = pathlib.Path(__file__).resolve().parent.parent
    script = (
        "import asyncio\n"
        "from sqlalchemy import text\n"
        "from app.core.database import engine\n"
        "async def main():\n"
        "    async with engine.begin() as conn:\n"
        f"{body}\n"
        "asyncio.run(main())\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, cwd=str(backend_root)
    )
    assert result.returncode == 0, result.stderr


def _backdate_encounter(encounter_id: str, days: int) -> None:
    _run_db_script(
        "        await conn.execute(\n"
        f"            text(\"UPDATE opd_encounters SET created_at = created_at - interval '{days} days' WHERE id = :id\"),\n"
        f"            {{'id': '{encounter_id}'}},\n"
        "        )"
    )


def _delete_encounter(encounter_id: str) -> None:
    """Backdating `created_at` (for the expired-QR test) permanently takes
    that row's `encounter_number` out of "today"'s count for its facility
    (see _generate_encounter_number in app/modules/opd/service.py) even
    after the row itself no longer matters to the test - left behind, it
    collides with a real registration reusing the same sequence number on a
    later run. Delete it outright instead of just cancelling its token."""
    _run_db_script(
        "        await conn.execute(text(\"DELETE FROM opd_tokens WHERE encounter_id = :id\"), {'id': '"
        + encounter_id
        + "'})\n"
        "        await conn.execute(text(\"DELETE FROM opd_encounters WHERE id = :id\"), {'id': '"
        + encounter_id
        + "'})"
    )


def _clear_active_and_waiting_tokens(client, doctor_id):
    """Cancels every non-terminal token in a doctor's queue. Test data isn't
    rolled back between runs (shared DB), and the invariants this file
    checks (e.g. "at most one active token") depend on starting from a
    known-clean queue, so this is run defensively before the tests that need
    it rather than relying on run order."""
    queue = client.get(f"/api/v1/opd/doctors/{doctor_id}/queue").json()["data"]
    for encounter in queue:
        token = encounter.get("token")
        if token and token["status"] in ("WAITING", "CALLED", "IN_CONSULTATION"):
            client.patch(f"/api/v1/opd/tokens/{token['id']}/status", json={"status": "CANCELLED"})


# ---------------------------------------------------------------------------
# 1. Invalid token transition
# ---------------------------------------------------------------------------


def test_invalid_token_transition_is_rejected(client):
    _login(client, RECEPTIONIST)
    encounter = _register_encounter(client)
    token_id = encounter["token"]["id"]
    assert encounter["token"]["status"] == "WAITING"

    # WAITING -> COMPLETED skips CALLED/IN_CONSULTATION entirely.
    response = client.patch(f"/api/v1/opd/tokens/{token_id}/status", json={"status": "COMPLETED"})

    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_TRANSITION"

    client.patch(f"/api/v1/opd/tokens/{token_id}/status", json={"status": "CANCELLED"})


def test_unknown_token_status_is_rejected(client):
    _login(client, RECEPTIONIST)
    encounter = _register_encounter(client)
    token_id = encounter["token"]["id"]

    response = client.patch(f"/api/v1/opd/tokens/{token_id}/status", json={"status": "TELEPORTED"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    client.patch(f"/api/v1/opd/tokens/{token_id}/status", json={"status": "CANCELLED"})


# ---------------------------------------------------------------------------
# 2. Concurrent token calls
# ---------------------------------------------------------------------------


def test_concurrent_call_next_admits_only_one_active_token(client):
    _login(client, RECEPTIONIST)
    _clear_active_and_waiting_tokens(client, DOCTOR_CARDIO_ID)

    _register_encounter(client, doctor_id=DOCTOR_CARDIO_ID, department_id=DEPT_CARDIO_ID)
    _register_encounter(client, doctor_id=DOCTOR_CARDIO_ID, department_id=DEPT_CARDIO_ID)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(client.post, f"/api/v1/opd/doctors/{DOCTOR_CARDIO_ID}/queue/call-next")
            for _ in range(2)
        ]
        results = [future.result() for future in futures]

    # Whether the two requests actually overlapped or were serialized by the
    # test client, the invariant under test is that they can never BOTH
    # succeed - the advisory lock plus the "already has an active token"
    # check must let exactly one through.
    statuses = sorted(result.status_code for result in results)
    assert statuses == [200, 409], [r.json() for r in results]

    conflict = next(r for r in results if r.status_code == 409)
    assert conflict.json()["error"]["code"] == "CONFLICT"

    _clear_active_and_waiting_tokens(client, DOCTOR_CARDIO_ID)


# ---------------------------------------------------------------------------
# 3. Unauthorized consultation update
# ---------------------------------------------------------------------------


def test_unauthorized_role_cannot_update_consultation(client):
    _login(client, RECEPTIONIST)
    encounter = _register_encounter(client, doctor_id=DOCTOR_CARDIO_ID, department_id=DEPT_CARDIO_ID)
    encounter_id = encounter["id"]

    _login(client, DOCTOR)  # dr.priya - the doctor actually assigned to this encounter
    started = client.post(f"/api/v1/opd/encounters/{encounter_id}/consultation", json={})
    assert started.status_code == 200

    # A receptionist has no consultations.manage permission at all.
    _login(client, RECEPTIONIST)
    forbidden = client.patch(
        f"/api/v1/opd/encounters/{encounter_id}/consultation", json={"diagnosis": "should not stick"}
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "FORBIDDEN"

    # Positive control: the actually-assigned doctor can update it.
    _login(client, DOCTOR)
    allowed = client.patch(
        f"/api/v1/opd/encounters/{encounter_id}/consultation", json={"diagnosis": "Confirmed by assigned doctor"}
    )
    assert allowed.status_code == 200
    assert allowed.json()["data"]["diagnosis"] == "Confirmed by assigned doctor"

    client.patch(f"/api/v1/opd/tokens/{encounter['token']['id']}/status", json={"status": "CANCELLED"})


# ---------------------------------------------------------------------------
# 4. Invalid QR
# ---------------------------------------------------------------------------


def test_invalid_qr_code_is_reported_not_raised(client):
    _login(client, RECEPTIONIST)

    response = client.post("/api/v1/opd/qr/verify", json={"qr_code": "this-is-not-a-real-code"})

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["valid"] is False
    assert body["reason"] == "INVALID"
    assert body["encounter"] is None


def test_tampered_qr_signature_is_invalid(client):
    _login(client, RECEPTIONIST)
    encounter = _register_encounter(client)
    qr_code = encounter["qr_code"]
    nonce, _, signature = qr_code.rpartition(".")
    tampered = f"{nonce}.{'0' if signature[0] != '0' else '1'}{signature[1:]}"

    response = client.post("/api/v1/opd/qr/verify", json={"qr_code": tampered})

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["valid"] is False
    assert body["reason"] == "INVALID"

    client.patch(f"/api/v1/opd/tokens/{encounter['token']['id']}/status", json={"status": "CANCELLED"})


# ---------------------------------------------------------------------------
# 6. Cross-facility QR access
# ---------------------------------------------------------------------------


def test_qr_from_another_tenant_is_reported_as_invalid(client):
    _login(client, RECEPTIONIST)
    encounter = _register_encounter(client)
    qr_code = encounter["qr_code"]

    # sunrise.admin is a HOSPITAL_ADMIN in a completely separate tenant/
    # facility (see test_multitenancy.py) - same role, same permission set,
    # but no legitimate access to this encounter's tenant.
    _login(client, SUNRISE_ADMIN)
    response = client.post("/api/v1/opd/qr/verify", json={"qr_code": qr_code})

    assert response.status_code == 200
    body = response.json()["data"]
    # Reported identically to an unknown code - confirming a QR exists in
    # another tenant would itself be a cross-tenant data leak.
    assert body["valid"] is False
    assert body["reason"] == "INVALID"
    assert body["encounter"] is None

    _login(client, RECEPTIONIST)
    client.patch(f"/api/v1/opd/tokens/{encounter['token']['id']}/status", json={"status": "CANCELLED"})


# ---------------------------------------------------------------------------
# 5. Expired QR
#
# Deliberately the LAST test in this file: backdating an encounter's
# `created_at` shifts it out of "today" for the per-facility, per-day
# encounter_number sequence (see _generate_encounter_number in
# app/modules/opd/service.py), which would collide with a later test's
# freshly-generated number for the same facility/day if anything after this
# one registered a new encounter. Nothing in this file runs after it.
# ---------------------------------------------------------------------------


def test_expired_qr_code_is_rejected(client):
    _login(client, RECEPTIONIST)
    encounter = _register_encounter(client)
    qr_code = encounter["qr_code"]
    encounter_id = encounter["id"]

    _backdate_encounter(encounter_id, days=2)

    response = client.post("/api/v1/opd/qr/verify", json={"qr_code": qr_code})

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["valid"] is False
    assert body["reason"] == "EXPIRED"
    assert body["encounter"]["id"] == encounter_id

    _delete_encounter(encounter_id)
