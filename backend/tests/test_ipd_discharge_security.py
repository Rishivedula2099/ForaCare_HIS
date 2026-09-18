"""P4-B06 (discharge) and P4-B07 (security integration) tests for the IPD
module. Discharge coverage here is audit/close/release-focused; the
double-discharge and bed-cleaning-not-available state machine tests already
live in test_ipd_security.py/test_ipd_state_machine.py. Security coverage
checks the full facility/role/ownership/cross-tenant/audit checklist against
every sensitive IPD write, not just admission/transfer (already covered in
test_ipd_security.py). Mirrors those files' conventions - demo-seeded fixed
UUIDs, shared DB, no per-test rollback.
"""

DEMO_PASSWORD = "Demo@123"

RECEPTIONIST = "receptionist"
HOSPITAL_ADMIN = "hospital.admin"
SUNRISE_ADMIN = "sunrise.admin"

# Seeded by 20260918_0902_f83c5a1e6d92_seed_demo_ipd_data.py
BED_101_A_ID = "99999999-9999-9999-9999-999999999901"

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


def _latest_audit_entry(client, *, resource_id: str, action: str) -> dict:
    logs = client.get("/api/v1/audit/logs", params={"resource_type": "ipd_admission", "limit": 200})
    assert logs.status_code == 200, logs.text
    entries = [e for e in logs.json()["data"] if e["resource_id"] == resource_id and e["action"] == action]
    assert len(entries) >= 1, f"no audit entry found for {action} on {resource_id}"
    return entries[0]


# ---------------------------------------------------------------------------
# P4-B06 - Discharge API
# ---------------------------------------------------------------------------


def test_discharge_closes_admission_releases_bed_and_is_audited(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    admission = _admit(client, patient_id=PATIENT_1_ID, bed_id=BED_101_A_ID)

    response = client.post(
        f"/api/v1/ipd/admissions/{admission['id']}/discharge",
        json={"discharge_type": "NORMAL", "discharge_summary": "Recovered, stable on discharge."},
    )
    assert response.status_code == 200, response.text

    # Close admission.
    fetched = client.get(f"/api/v1/ipd/admissions/{admission['id']}").json()["data"]
    assert fetched["status"] == "DISCHARGED"

    # Release bed (freed for cleaning, not left OCCUPIED).
    bed = _find_bed(client, BED_101_A_ID)
    assert bed["status"] == "CLEANING"
    assert bed.get("current_occupant") is None

    # Audit discharge, with before/after state.
    entry = _latest_audit_entry(client, resource_id=admission["id"], action="ipd.discharge_created")
    assert entry["before"]["admission_status"] == "ADMITTED"
    assert entry["before"]["bed_status"] == "OCCUPIED"
    assert entry["after"]["admission_status"] == "DISCHARGED"
    assert entry["after"]["discharge_summary"] == "Recovered, stable on discharge."

    client.patch(f"/api/v1/ipd/beds/{BED_101_A_ID}", json={"status": "AVAILABLE"})


def test_discharge_validates_admission_is_active(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    admission = _admit(client, patient_id=PATIENT_1_ID, bed_id=BED_101_A_ID)
    client.post(f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"})

    response = client.post(
        f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"}
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"


# ---------------------------------------------------------------------------
# P4-B07 - Security integration checklist, exercised against consent and
# discharge (admission/transfer/bed already covered in test_ipd_security.py
# and test_ipd_transfer.py).
# ---------------------------------------------------------------------------


def test_view_only_role_cannot_record_consent_or_discharge(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    admission = _admit(client, patient_id=PATIENT_1_ID, bed_id=BED_101_A_ID)

    _login(client, RECEPTIONIST)
    consent = client.post(
        f"/api/v1/ipd/admissions/{admission['id']}/consents",
        json={"consent_type": "GENERAL_ADMISSION", "given_by_name": "Sunita Verma"},
    )
    assert consent.status_code == 403
    assert consent.json()["error"]["code"] == "FORBIDDEN"

    discharge = client.post(
        f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"}
    )
    assert discharge.status_code == 403
    assert discharge.json()["error"]["code"] == "FORBIDDEN"

    # Read access to consents remains available to a view-only role.
    list_consents = client.get(f"/api/v1/ipd/admissions/{admission['id']}/consents")
    assert list_consents.status_code == 200

    _login(client, HOSPITAL_ADMIN)
    client.post(f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"})
    client.patch(f"/api/v1/ipd/beds/{BED_101_A_ID}", json={"status": "AVAILABLE"})


def test_cross_tenant_consent_and_discharge_are_not_found(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    admission = _admit(client, patient_id=PATIENT_1_ID, bed_id=BED_101_A_ID)

    _login(client, SUNRISE_ADMIN)
    consent = client.post(
        f"/api/v1/ipd/admissions/{admission['id']}/consents",
        json={"consent_type": "GENERAL_ADMISSION", "given_by_name": "Someone Else"},
    )
    assert consent.status_code == 404
    assert consent.json()["error"]["code"] == "NOT_FOUND"

    list_consents = client.get(f"/api/v1/ipd/admissions/{admission['id']}/consents")
    assert list_consents.status_code == 404

    discharge = client.post(
        f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"}
    )
    assert discharge.status_code == 404
    assert discharge.json()["error"]["code"] == "NOT_FOUND"

    _login(client, HOSPITAL_ADMIN)
    client.post(f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"})
    client.patch(f"/api/v1/ipd/beds/{BED_101_A_ID}", json={"status": "AVAILABLE"})


def test_consent_recording_is_audited(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    admission = _admit(client, patient_id=PATIENT_1_ID, bed_id=BED_101_A_ID)

    response = client.post(
        f"/api/v1/ipd/admissions/{admission['id']}/consents",
        json={"consent_type": "GENERAL_ADMISSION", "given_by_name": "Sunita Verma", "consent_given": True},
    )
    assert response.status_code == 200, response.text

    entry = _latest_audit_entry(client, resource_id=admission["id"], action="ipd.consent_recorded")
    assert entry["after"]["consent_type"] == "GENERAL_ADMISSION"
    assert entry["after"]["given_by_name"] == "Sunita Verma"

    client.post(f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"})
    client.patch(f"/api/v1/ipd/beds/{BED_101_A_ID}", json={"status": "AVAILABLE"})
