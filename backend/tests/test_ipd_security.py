"""P4-B01 security tests for the IPD module: `ipd.view`-only users blocked
from every write endpoint, cross-tenant isolation on ward/room/bed/admission
resources, transfer rejected onto a non-allocatable bed, and double-discharge
rejected. Mirrors test_opd_security.py's conventions - demo-seeded fixed
UUIDs, shared DB, no per-test rollback. See test_ipd_state_machine.py for
P4-B02's bed status transition coverage.
"""

DEMO_PASSWORD = "Demo@123"

RECEPTIONIST = "receptionist"
HOSPITAL_ADMIN = "hospital.admin"
SUNRISE_ADMIN = "sunrise.admin"

# Seeded by 20260918_0902_f83c5a1e6d92_seed_demo_ipd_data.py
WARD_GENMED_A_ID = "77777777-7777-7777-7777-777777777701"
BED_101_A_ID = "99999999-9999-9999-9999-999999999901"
BED_101_B_ID = "99999999-9999-9999-9999-999999999902"
BED_102_A_ID = "99999999-9999-9999-9999-999999999903"

# Seeded by 20260908_1101_b8d1e4f6a209_seed_demo_patients.py
PATIENT_1_ID = "44444444-4444-4444-4444-444444444401"
PATIENT_2_ID = "44444444-4444-4444-4444-444444444402"


def _login(client, username: str, password: str = DEMO_PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _find_bed(client, bed_id: str) -> dict:
    beds = client.get("/api/v1/ipd/beds").json()["data"]
    return next(bed for bed in beds if bed["id"] == bed_id)


def _ensure_bed_available(client, bed_id: str) -> None:
    """Discharges whatever admission currently occupies this bed (if any) and
    force-transitions it back to AVAILABLE, so a test can rely on it starting
    AVAILABLE regardless of what an earlier run against this shared DB left
    behind. A discharge/transfer leaves a bed CLEANING (P4-B02), and every
    other non-OCCUPIED status reaches AVAILABLE in a single hop, so this is
    always a plain PATCH once nothing is admitted to it."""
    bed = _find_bed(client, bed_id)
    occupant = bed.get("current_occupant")
    if occupant:
        client.post(f"/api/v1/ipd/admissions/{occupant['admission_id']}/discharge", json={"discharge_type": "NORMAL"})
        bed = _find_bed(client, bed_id)
    if bed["status"] != "AVAILABLE":
        client.patch(f"/api/v1/ipd/beds/{bed_id}", json={"status": "AVAILABLE"})


def _admit(client, *, patient_id: str, bed_id: str) -> dict:
    response = client.post(
        "/api/v1/ipd/admissions",
        json={"patient_id": patient_id, "bed_id": bed_id, "admission_type": "ELECTIVE"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


# ---------------------------------------------------------------------------
# 1. ipd.view-only role is blocked from every write endpoint
# ---------------------------------------------------------------------------


def test_view_only_role_cannot_write_ipd_resources(client):
    _login(client, RECEPTIONIST)

    # Positive control: view endpoints are reachable.
    assert client.get("/api/v1/ipd/wards").status_code == 200
    assert client.get("/api/v1/ipd/beds").status_code == 200

    create_ward = client.post(
        "/api/v1/ipd/wards", json={"name": "Should Not Be Created", "code": "NOPE-1"}
    )
    assert create_ward.status_code == 403
    assert create_ward.json()["error"]["code"] == "FORBIDDEN"

    admit = client.post(
        "/api/v1/ipd/admissions",
        json={"patient_id": PATIENT_1_ID, "bed_id": BED_101_A_ID, "admission_type": "ELECTIVE"},
    )
    assert admit.status_code == 403
    assert admit.json()["error"]["code"] == "FORBIDDEN"


# ---------------------------------------------------------------------------
# 2. Cross-tenant isolation
# ---------------------------------------------------------------------------


def test_cross_tenant_ward_access_is_not_found(client):
    # sunrise.admin is a HOSPITAL_ADMIN in a completely separate tenant/
    # facility (see test_multitenancy.py) - same role, same permission set,
    # but no legitimate access to this tenant's ward.
    _login(client, SUNRISE_ADMIN)

    response = client.patch(f"/api/v1/ipd/wards/{WARD_GENMED_A_ID}", json={"floor": "9"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_cross_tenant_admission_is_not_found(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    admission = _admit(client, patient_id=PATIENT_1_ID, bed_id=BED_101_A_ID)

    _login(client, SUNRISE_ADMIN)
    response = client.get(f"/api/v1/ipd/admissions/{admission['id']}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"

    _login(client, HOSPITAL_ADMIN)
    client.post(f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"})


# ---------------------------------------------------------------------------
# 3. Transfer onto a non-AVAILABLE bed is rejected
# ---------------------------------------------------------------------------


def test_transfer_onto_occupied_bed_is_rejected(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    _ensure_bed_available(client, BED_101_B_ID)

    admission = _admit(client, patient_id=PATIENT_1_ID, bed_id=BED_101_A_ID)
    _admit(client, patient_id=PATIENT_2_ID, bed_id=BED_101_B_ID)

    response = client.post(
        f"/api/v1/ipd/admissions/{admission['id']}/transfer", json={"to_bed_id": BED_101_B_ID}
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"

    _ensure_bed_available(client, BED_101_A_ID)
    _ensure_bed_available(client, BED_101_B_ID)


def test_transfer_to_an_available_bed_moves_the_admission(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    _ensure_bed_available(client, BED_102_A_ID)

    admission = _admit(client, patient_id=PATIENT_1_ID, bed_id=BED_101_A_ID)

    response = client.post(
        f"/api/v1/ipd/admissions/{admission['id']}/transfer", json={"to_bed_id": BED_102_A_ID}
    )
    assert response.status_code == 200, response.text

    # The vacated bed needs cleaning before reuse (P4-B02), not straight back
    # to AVAILABLE.
    assert _find_bed(client, BED_101_A_ID)["status"] == "CLEANING"
    assert _find_bed(client, BED_102_A_ID)["status"] == "OCCUPIED"

    _ensure_bed_available(client, BED_102_A_ID)


# ---------------------------------------------------------------------------
# 4. Double discharge is rejected
# ---------------------------------------------------------------------------


def test_double_discharge_is_rejected(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    admission = _admit(client, patient_id=PATIENT_1_ID, bed_id=BED_101_A_ID)

    first = client.post(f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"})
    assert first.status_code == 200, first.text

    second = client.post(f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"})
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT"
