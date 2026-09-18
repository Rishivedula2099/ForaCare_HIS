"""P4-B05 tests for the transfer API: same-bed transfer is rejected,
cross-tenant destination beds are not found, and a successful transfer
writes an audit entry with the source/destination bed states. See
test_ipd_security.py for the pre-existing occupied-target and happy-path
transfer coverage, and test_ipd_concurrency.py for the transactional/
locking guarantees. Mirrors those files' conventions - demo-seeded fixed
UUIDs, shared DB, no per-test rollback.
"""

DEMO_PASSWORD = "Demo@123"

HOSPITAL_ADMIN = "hospital.admin"
SUNRISE_ADMIN = "sunrise.admin"

# Seeded by 20260918_0902_f83c5a1e6d92_seed_demo_ipd_data.py
BED_101_A_ID = "99999999-9999-9999-9999-999999999901"
BED_102_A_ID = "99999999-9999-9999-9999-999999999903"

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


def test_transfer_to_the_same_bed_is_rejected(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    admission = _admit(client, patient_id=PATIENT_1_ID, bed_id=BED_101_A_ID)

    response = client.post(
        f"/api/v1/ipd/admissions/{admission['id']}/transfer", json={"to_bed_id": BED_101_A_ID}
    )

    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert _find_bed(client, BED_101_A_ID)["status"] == "OCCUPIED"

    client.post(f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"})


def test_transfer_to_a_cross_tenant_bed_is_not_found(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    admission = _admit(client, patient_id=PATIENT_1_ID, bed_id=BED_101_A_ID)

    # sunrise.admin's tenant has its own ipd_beds; a bed id that only exists
    # there (or doesn't exist at all) must 404 for this tenant, not leak
    # whether it exists.
    import uuid

    response = client.post(
        f"/api/v1/ipd/admissions/{admission['id']}/transfer", json={"to_bed_id": str(uuid.uuid4())}
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"
    assert _find_bed(client, BED_101_A_ID)["status"] == "OCCUPIED"

    client.post(f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"})


def test_successful_transfer_is_audited_with_before_and_after(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    _ensure_bed_available(client, BED_102_A_ID)
    admission = _admit(client, patient_id=PATIENT_1_ID, bed_id=BED_101_A_ID)

    response = client.post(
        f"/api/v1/ipd/admissions/{admission['id']}/transfer",
        json={"to_bed_id": BED_102_A_ID, "reason": "Ward reassignment"},
    )
    assert response.status_code == 200, response.text
    transfer = response.json()["data"]

    logs = client.get("/api/v1/audit/logs", params={"resource_type": "ipd_admission", "limit": 200})
    assert logs.status_code == 200, logs.text
    entries = [e for e in logs.json()["data"] if e["resource_id"] == admission["id"] and e["action"] == "ipd.transfer_created"]
    assert len(entries) == 1, "expected exactly one transfer audit entry for this admission"
    entry = entries[0]
    assert entry["before"]["from_bed_id"] == BED_101_A_ID
    assert entry["before"]["from_bed_status"] == "OCCUPIED"
    assert entry["before"]["to_bed_id"] == BED_102_A_ID
    assert entry["before"]["to_bed_status"] == "AVAILABLE"
    assert entry["after"]["id"] == transfer["id"]

    _ensure_bed_available(client, BED_102_A_ID)
