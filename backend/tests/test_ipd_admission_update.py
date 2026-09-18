"""P4-B04 tests for admission update and the deposit ledger: referral/payment
category fields round-trip through create and update, `ipd.view`-only users
are blocked from every write, cross-tenant admissions are not found, and
deposits recorded at admission time plus afterwards both show up in the
ledger. Mirrors test_ipd_security.py's conventions - demo-seeded fixed
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


def _admit(client, *, patient_id: str, bed_id: str, **extra) -> dict:
    payload = {"patient_id": patient_id, "bed_id": bed_id, "admission_type": "ELECTIVE", **extra}
    response = client.post("/api/v1/ipd/admissions", json=payload)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_admission_create_defaults_and_initial_deposit(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)

    admission = _admit(
        client,
        patient_id=PATIENT_1_ID,
        bed_id=BED_101_A_ID,
        referral_source="HOSPITAL",
        referral_detail="City Hospital",
        payment_category="INSURANCE",
        deposit_amount=5000,
        deposit_payment_mode="UPI",
    )

    assert admission["referral_source"] == "HOSPITAL"
    assert admission["referral_detail"] == "City Hospital"
    assert admission["payment_category"] == "INSURANCE"
    assert len(admission["deposits"]) == 1
    assert admission["deposits"][0]["amount"] == 5000.0
    assert admission["deposits"][0]["payment_mode"] == "UPI"

    client.post(f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"})


def test_view_only_role_cannot_update_admission_or_record_deposit(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    admission = _admit(client, patient_id=PATIENT_1_ID, bed_id=BED_101_A_ID)

    _login(client, RECEPTIONIST)
    update = client.patch(f"/api/v1/ipd/admissions/{admission['id']}", json={"payment_category": "CORPORATE"})
    assert update.status_code == 403
    assert update.json()["error"]["code"] == "FORBIDDEN"

    deposit = client.post(f"/api/v1/ipd/admissions/{admission['id']}/deposits", json={"amount": 1000})
    assert deposit.status_code == 403
    assert deposit.json()["error"]["code"] == "FORBIDDEN"

    _login(client, HOSPITAL_ADMIN)
    client.post(f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"})


def test_update_admission_changes_referral_and_payment_category(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    admission = _admit(client, patient_id=PATIENT_1_ID, bed_id=BED_101_A_ID)

    response = client.patch(
        f"/api/v1/ipd/admissions/{admission['id']}",
        json={"referral_source": "CAMP", "referral_detail": "Health Camp", "payment_category": "GOVERNMENT_SCHEME"},
    )
    assert response.status_code == 200, response.text
    updated = response.json()["data"]
    assert updated["referral_source"] == "CAMP"
    assert updated["referral_detail"] == "Health Camp"
    assert updated["payment_category"] == "GOVERNMENT_SCHEME"

    client.post(f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"})


def test_cross_tenant_admission_update_and_deposit_are_not_found(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    admission = _admit(client, patient_id=PATIENT_1_ID, bed_id=BED_101_A_ID)

    _login(client, SUNRISE_ADMIN)
    update = client.patch(f"/api/v1/ipd/admissions/{admission['id']}", json={"payment_category": "CASH"})
    assert update.status_code == 404
    assert update.json()["error"]["code"] == "NOT_FOUND"

    deposit = client.post(f"/api/v1/ipd/admissions/{admission['id']}/deposits", json={"amount": 500})
    assert deposit.status_code == 404
    assert deposit.json()["error"]["code"] == "NOT_FOUND"

    _login(client, HOSPITAL_ADMIN)
    client.post(f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"})


def test_deposit_ledger_accumulates_multiple_entries(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    admission = _admit(client, patient_id=PATIENT_1_ID, bed_id=BED_101_A_ID, deposit_amount=2000)

    second = client.post(
        f"/api/v1/ipd/admissions/{admission['id']}/deposits", json={"amount": 1500, "payment_mode": "CARD"}
    )
    assert second.status_code == 200, second.text

    listed = client.get(f"/api/v1/ipd/admissions/{admission['id']}/deposits")
    assert listed.status_code == 200
    amounts = sorted(d["amount"] for d in listed.json()["data"])
    assert amounts == [1500.0, 2000.0]

    client.post(f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"})


def test_discharged_admission_cannot_be_updated_or_receive_deposits(client):
    _login(client, HOSPITAL_ADMIN)
    _ensure_bed_available(client, BED_101_A_ID)
    admission = _admit(client, patient_id=PATIENT_1_ID, bed_id=BED_101_A_ID)
    client.post(f"/api/v1/ipd/admissions/{admission['id']}/discharge", json={"discharge_type": "NORMAL"})

    update = client.patch(f"/api/v1/ipd/admissions/{admission['id']}", json={"payment_category": "CASH"})
    assert update.status_code == 409
    assert update.json()["error"]["code"] == "CONFLICT"

    deposit = client.post(f"/api/v1/ipd/admissions/{admission['id']}/deposits", json={"amount": 100})
    assert deposit.status_code == 409
    assert deposit.json()["error"]["code"] == "CONFLICT"
