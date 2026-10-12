"""P8-B02/B05: ABHA verify -> link -> consent -> unlink workflow and its
authorization, against the real API with the mock ABDM adapter. Requires the
seeded demo database (all demo users share one facility except lab.tech)."""
import pytest

DEMO_PASSWORD = "Demo@123"
RECEPTIONIST = "receptionist"  # patients.link_abha, no patients.unlink_abha
HOSPITAL_ADMIN = "hospital.admin"  # both
DOCTOR = "dr.priya"  # patients.manage but neither ABHA permission
LAB_TECH = "lab.tech"
PATIENT_1 = "44444444-4444-4444-4444-444444444401"
PATIENT_2 = "44444444-4444-4444-4444-444444444402"


def _base(patient_id: str) -> str:
    return f"/api/v1/abdm/patients/{patient_id}/abha"


def _login(client, username: str):
    response = client.post("/api/v1/auth/login", json={"username": username, "password": DEMO_PASSWORD})
    assert response.status_code == 200, response.text


def _verify(client, patient_id: str = PATIENT_1, identifier: str = "9876543210"):
    otp = client.post("/api/v1/abdm/otp", json={"auth_method": "MOBILE_OTP", "identifier": identifier})
    assert otp.status_code == 200, otp.text
    txn = otp.json()["data"]["transaction_id"]
    return client.post(f"{_base(patient_id)}/verify", json={"transaction_id": txn, "otp": "123456"})


def _reset(client):
    """Leaves the seeded patients unlinked (admin holds the unlink permission)."""
    client.cookies.clear()
    _login(client, HOSPITAL_ADMIN)
    for patient_id in (PATIENT_1, PATIENT_2):
        if client.get(_base(patient_id)).json()["data"]["status"] != "UNVERIFIED":
            client.delete(_base(patient_id))
    client.cookies.clear()


@pytest.fixture
def clean(client):
    _reset(client)
    yield client
    _reset(client)


def test_requires_authentication(client):
    assert client.get(_base(PATIENT_1)).status_code == 401
    assert client.post("/api/v1/abdm/otp", json={}).status_code == 401


def test_full_workflow(clean):
    _login(clean, RECEPTIONIST)
    base = _base(PATIENT_1)
    assert clean.get(base).json()["data"]["status"] == "UNVERIFIED"

    verified = _verify(clean)
    assert verified.status_code == 200, verified.text
    data = verified.json()["data"]
    assert data["status"] == "VERIFIED" and data["abha_number"] and data["linked_at"] is None

    # consent needs a LINKED ABHA
    assert clean.post(f"{base}/consents", json={"purpose": "CARE_MANAGEMENT"}).status_code == 409

    linked = clean.post(f"{base}/link")
    assert linked.status_code == 200
    assert linked.json()["data"]["status"] == "LINKED"
    assert linked.json()["data"]["linked_at"] is not None

    consent = clean.post(f"{base}/consents", json={"purpose": "CARE_MANAGEMENT"})
    assert consent.status_code == 200, consent.text
    consent_id = consent.json()["data"]["id"]
    assert clean.post(f"{base}/consents", json={"purpose": "CARE_MANAGEMENT"}).status_code == 409

    revoked = clean.post(f"{base}/consents/{consent_id}/revoke")
    assert revoked.json()["data"]["status"] == "REVOKED"
    assert clean.post(f"{base}/consents/{consent_id}/revoke").status_code == 409
    assert clean.post(f"{base}/consents", json={"purpose": "RESEARCH"}).status_code == 200

    # a receptionist can link but not unlink; the admin can
    assert clean.delete(base).status_code == 403
    clean.cookies.clear()
    _login(clean, HOSPITAL_ADMIN)
    unlinked = clean.delete(base)
    assert unlinked.status_code == 200
    status = unlinked.json()["data"]
    assert status["status"] == "UNVERIFIED" and status["abha_number"] is None
    assert all(c["status"] == "REVOKED" for c in status["consents"])


def test_link_requires_verification(clean):
    _login(clean, RECEPTIONIST)
    assert clean.post(f"{_base(PATIENT_1)}/link").status_code == 409


def test_bad_otp_and_unknown_transaction_are_rejected(clean):
    _login(clean, RECEPTIONIST)
    base = _base(PATIENT_1)
    assert clean.post(f"{base}/verify", json={"transaction_id": "nope", "otp": "123456"}).status_code == 400
    assert clean.post(f"{base}/verify", json={"transaction_id": "x", "otp": "12"}).status_code == 422


@pytest.mark.parametrize("username", [DOCTOR, LAB_TECH])
def test_roles_without_the_abha_permissions_cannot_link_or_unlink(clean, username):
    _login(clean, username)
    base = _base(PATIENT_1)
    assert clean.post("/api/v1/abdm/otp", json={"auth_method": "MOBILE_OTP", "identifier": "9876543210"}).status_code == 403
    assert clean.post(f"{base}/verify", json={"transaction_id": "t", "otp": "123456"}).status_code == 403
    assert clean.post(f"{base}/link").status_code == 403
    assert clean.post(f"{base}/consents", json={"purpose": "RESEARCH"}).status_code == 403
    assert clean.delete(base).status_code == 403


def test_one_abha_cannot_be_linked_to_two_patients(clean):
    _login(clean, RECEPTIONIST)
    assert _verify(clean, PATIENT_1, identifier="9876543210").status_code == 200
    assert clean.post(f"{_base(PATIENT_1)}/link").status_code == 200
    # the mock derives the same ABHA from the same identifier
    second = _verify(clean, PATIENT_2, identifier="9876543210")
    assert second.status_code == 409


def test_linked_patient_cannot_silently_switch_to_a_different_abha(clean):
    _login(clean, RECEPTIONIST)
    assert _verify(clean, identifier="9876543210").status_code == 200
    assert clean.post(f"{_base(PATIENT_1)}/link").status_code == 200
    assert _verify(clean, identifier="9123456789").status_code == 409
    # re-verifying the same ABHA is fine and keeps it linked
    again = _verify(clean, identifier="9876543210")
    assert again.status_code == 200 and again.json()["data"]["status"] == "LINKED"


def test_patient_uid_is_unchanged_by_linking_and_unlinking(clean):
    _login(clean, RECEPTIONIST)
    before = clean.get(f"/api/v1/patients/{PATIENT_1}").json()["data"]
    assert _verify(clean).status_code == 200
    assert clean.post(f"{_base(PATIENT_1)}/link").status_code == 200
    linked = clean.get(f"/api/v1/patients/{PATIENT_1}").json()["data"]
    assert linked["uid"] == before["uid"] and linked["mrn"] == before["mrn"]
    assert [l["system"] for l in linked["identity_links"]] == ["ABHA"]

    clean.cookies.clear()
    _login(clean, HOSPITAL_ADMIN)
    assert clean.delete(_base(PATIENT_1)).status_code == 200
    after = clean.get(f"/api/v1/patients/{PATIENT_1}").json()["data"]
    assert after["uid"] == before["uid"] and after["id"] == before["id"]


def test_patient_update_cannot_modify_abha_link_or_uid(clean):
    _login(clean, RECEPTIONIST)
    assert _verify(clean).status_code == 200
    original = clean.get(f"/api/v1/patients/{PATIENT_1}").json()["data"]
    clean.patch(
        f"/api/v1/patients/{PATIENT_1}",
        json={"uid": "HACKED-1", "identity_links": [], "first_name": original["first_name"]},
    )
    after = clean.get(f"/api/v1/patients/{PATIENT_1}").json()["data"]
    assert after["uid"] == original["uid"]
    assert after["identity_links"] == original["identity_links"] != []
