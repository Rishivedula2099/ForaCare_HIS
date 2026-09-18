"""P4-B02 tests for the IPD bed state machine: invalid/valid manual status
transitions on `PATCH /ipd/beds/{id}`, discharge/transfer leaving a bed
CLEANING rather than AVAILABLE, and a patient being blocked from holding two
simultaneous admissions. Mirrors test_ipd_security.py's conventions -
demo-seeded fixed UUIDs, shared DB, no per-test rollback.
"""

DEMO_PASSWORD = "Demo@123"
HOSPITAL_ADMIN = "hospital.admin"

# Seeded by 20260918_0902_f83c5a1e6d92_seed_demo_ipd_data.py
BED_101_A_ID = "99999999-9999-9999-9999-999999999901"
BED_ICU_1_ID = "99999999-9999-9999-9999-999999999905"

# Seeded by 20260908_1101_b8d1e4f6a209_seed_demo_patients.py
PATIENT_1_ID = "44444444-4444-4444-4444-444444444401"


def _login(client, username: str, password: str = DEMO_PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _find_bed(client, bed_id: str) -> dict:
    beds = client.get("/api/v1/ipd/beds").json()["data"]
    return next(bed for bed in beds if bed["id"] == bed_id)


def _ensure_bed_available(client, bed_id: str) -> None:
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
# 1. Manual transitions
# ---------------------------------------------------------------------------


def test_invalid_manual_transition_is_rejected(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_ICU_1_ID)

    # AVAILABLE -> OCCUPIED is a system-only transition (via admission), not
    # a manual one.
    response = client.patch(f"/api/v1/ipd/beds/{BED_ICU_1_ID}", json={"status": "OCCUPIED"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_TRANSITION"
    assert _find_bed(client, BED_ICU_1_ID)["status"] == "AVAILABLE"


def test_unknown_status_value_is_a_validation_error(client):
    _login(client, HOSPITAL_ADMIN)

    response = client.patch(f"/api/v1/ipd/beds/{BED_ICU_1_ID}", json={"status": "ON_FIRE"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_valid_manual_transition_cycle_succeeds(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_ICU_1_ID)

    to_maintenance = client.patch(f"/api/v1/ipd/beds/{BED_ICU_1_ID}", json={"status": "MAINTENANCE"})
    assert to_maintenance.status_code == 200, to_maintenance.text
    assert to_maintenance.json()["data"]["status"] == "MAINTENANCE"

    to_blocked = client.patch(f"/api/v1/ipd/beds/{BED_ICU_1_ID}", json={"status": "BLOCKED"})
    assert to_blocked.status_code == 200, to_blocked.text
    assert to_blocked.json()["data"]["status"] == "BLOCKED"

    # BLOCKED -> RESERVED is not a direct transition; must go via AVAILABLE
    # or MAINTENANCE first.
    direct_to_reserved = client.patch(f"/api/v1/ipd/beds/{BED_ICU_1_ID}", json={"status": "RESERVED"})
    assert direct_to_reserved.status_code == 400
    assert direct_to_reserved.json()["error"]["code"] == "INVALID_TRANSITION"

    back_to_available = client.patch(f"/api/v1/ipd/beds/{BED_ICU_1_ID}", json={"status": "AVAILABLE"})
    assert back_to_available.status_code == 200, back_to_available.text
    assert back_to_available.json()["data"]["status"] == "AVAILABLE"


# ---------------------------------------------------------------------------
# 2. Discharge leaves a bed CLEANING, not AVAILABLE
# ---------------------------------------------------------------------------


def test_discharge_leaves_bed_cleaning_not_available(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    admission = _admit(client, patient_id=PATIENT_1_ID, bed_id=BED_101_A_ID)

    discharge = client.post(
        f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"}
    )
    assert discharge.status_code == 200, discharge.text
    assert _find_bed(client, BED_101_A_ID)["status"] == "CLEANING"

    cleaned = client.patch(f"/api/v1/ipd/beds/{BED_101_A_ID}", json={"status": "AVAILABLE"})
    assert cleaned.status_code == 200, cleaned.text


# ---------------------------------------------------------------------------
# 3. A patient cannot hold two simultaneous admissions
# ---------------------------------------------------------------------------


def test_patient_cannot_be_admitted_twice(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    _ensure_bed_available(client, BED_ICU_1_ID)

    admission = _admit(client, patient_id=PATIENT_1_ID, bed_id=BED_101_A_ID)

    second = client.post(
        "/api/v1/ipd/admissions",
        json={"patient_id": PATIENT_1_ID, "bed_id": BED_ICU_1_ID, "admission_type": "ELECTIVE"},
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT"
    # The second bed was never touched by the rejected admission attempt.
    assert _find_bed(client, BED_ICU_1_ID)["status"] == "AVAILABLE"

    client.post(f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"})
    _ensure_bed_available(client, BED_101_A_ID)
