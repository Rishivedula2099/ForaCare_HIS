import io
import itertools
import time

DEMO_PASSWORD = "Demo@123"

# Test data isn't rolled back between runs (the DB is shared, real state),
# so a fixed starting number would collide with patients left over from a
# previous run. Seed from the current time instead of a constant so each
# run gets a fresh, non-colliding range.
_mobile_sequence = itertools.count(9_000_000_000 + (int(time.time()) % 90_000_000))

RECEPTIONIST = "receptionist"
DOCTOR = "dr.priya"
NURSE = "nurse.mary"
SUNRISE_ADMIN = "sunrise.admin"

SEEDED_PATIENT_ID = "44444444-4444-4444-4444-444444444401"
SEEDED_PATIENT_MOBILE = "9876543210"


def _login(client, username: str, password: str = DEMO_PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _new_patient_payload(**overrides) -> dict:
    unique = next(_mobile_sequence)
    payload = {
        "first_name": "Test",
        "last_name": f"Patient{unique}",
        "gender": "MALE",
        "dob": "1990-01-01",
        "blood_group": "O_POSITIVE",
        "address": {
            "street": "1 Test Street",
            "city": "Bengaluru",
            "state": "Karnataka",
            "pincode": "560001",
        },
        "contacts": [{"contact_type": "MOBILE", "value": str(unique), "is_primary": True}],
        "identifiers": [],
    }
    payload.update(overrides)
    return payload


def test_create_list_get_update_round_trip(client):
    _login(client, RECEPTIONIST)

    create_response = client.post("/api/v1/patients", json=_new_patient_payload())
    assert create_response.status_code == 200
    patient = create_response.json()["data"]
    assert patient["uid"]
    assert patient["mrn"]
    patient_id = patient["id"]

    list_response = client.get("/api/v1/patients")
    assert list_response.status_code == 200
    assert any(p["id"] == patient_id for p in list_response.json()["data"])

    get_response = client.get(f"/api/v1/patients/{patient_id}")
    assert get_response.status_code == 200
    assert get_response.json()["data"]["first_name"] == "Test"

    update_response = client.patch(
        f"/api/v1/patients/{patient_id}", json={"occupation": "Carpenter"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["occupation"] == "Carpenter"


def test_create_rejects_duplicate_mobile(client):
    _login(client, RECEPTIONIST)

    response = client.post(
        "/api/v1/patients",
        json=_new_patient_payload(
            contacts=[{"contact_type": "MOBILE", "value": SEEDED_PATIENT_MOBILE, "is_primary": True}]
        ),
    )
    assert response.status_code == 409


def test_check_duplicates_endpoint_finds_existing_patient(client):
    _login(client, RECEPTIONIST)

    response = client.post(
        "/api/v1/patients/check-duplicates", json={"mobile": SEEDED_PATIENT_MOBILE}
    )
    assert response.status_code == 200
    matches = response.json()["data"]
    assert any(m["id"] == SEEDED_PATIENT_ID for m in matches)


def test_view_only_role_cannot_create_or_update_patient(client):
    _login(client, NURSE)

    create_response = client.post("/api/v1/patients", json=_new_patient_payload())
    assert create_response.status_code == 403

    update_response = client.patch(
        f"/api/v1/patients/{SEEDED_PATIENT_ID}", json={"occupation": "X"}
    )
    assert update_response.status_code == 403

    # Nurses still have view access.
    get_response = client.get(f"/api/v1/patients/{SEEDED_PATIENT_ID}")
    assert get_response.status_code == 200


def test_cannot_fetch_another_tenants_patient(client):
    _login(client, SUNRISE_ADMIN)

    response = client.get(f"/api/v1/patients/{SEEDED_PATIENT_ID}")
    assert response.status_code == 404


def test_photo_upload_and_download_round_trip(client):
    _login(client, DOCTOR)

    create_response = client.post("/api/v1/patients", json=_new_patient_payload())
    patient_id = create_response.json()["data"]["id"]

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color="red").save(buffer, format="JPEG")
    buffer.seek(0)

    upload_response = client.post(
        f"/api/v1/patients/{patient_id}/photo",
        files={"file": ("photo.jpg", buffer, "image/jpeg")},
    )
    assert upload_response.status_code == 200
    photo_id = upload_response.json()["data"]["id"]

    download_response = client.get(f"/api/v1/patients/{patient_id}/photo/{photo_id}")
    assert download_response.status_code == 200
    assert download_response.headers["content-type"] == "image/jpeg"


def test_photo_upload_rejects_oversized_and_invalid_files(client):
    _login(client, DOCTOR)

    create_response = client.post("/api/v1/patients", json=_new_patient_payload())
    patient_id = create_response.json()["data"]["id"]

    invalid_response = client.post(
        f"/api/v1/patients/{patient_id}/photo",
        files={"file": ("not-a-photo.jpg", io.BytesIO(b"not an image"), "image/jpeg")},
    )
    assert invalid_response.status_code == 422

    oversized_response = client.post(
        f"/api/v1/patients/{patient_id}/photo",
        files={
            "file": (
                "big.jpg",
                io.BytesIO(b"\x00" * (5 * 1024 * 1024 + 1)),
                "image/jpeg",
            )
        },
    )
    assert oversized_response.status_code == 413


def test_another_tenant_cannot_download_photo(client):
    _login(client, DOCTOR)
    create_response = client.post("/api/v1/patients", json=_new_patient_payload())
    patient_id = create_response.json()["data"]["id"]

    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (10, 10), color="blue").save(buffer, format="JPEG")
    buffer.seek(0)
    upload_response = client.post(
        f"/api/v1/patients/{patient_id}/photo",
        files={"file": ("photo.jpg", buffer, "image/jpeg")},
    )
    photo_id = upload_response.json()["data"]["id"]

    _login(client, SUNRISE_ADMIN)
    response = client.get(f"/api/v1/patients/{patient_id}/photo/{photo_id}")
    assert response.status_code == 404


def test_patient_audit_events_are_recorded(client):
    _login(client, RECEPTIONIST)
    create_response = client.post("/api/v1/patients", json=_new_patient_payload())
    patient_id = create_response.json()["data"]["id"]

    client.get(f"/api/v1/patients/{patient_id}")
    client.patch(f"/api/v1/patients/{patient_id}", json={"occupation": "Driver"})

    _login(client, "hospital.admin")
    logs = client.get(
        "/api/v1/audit/logs", params={"resource_type": "patient"}
    ).json()["data"]
    actions = {log["action"] for log in logs if log["resource_id"] == patient_id}
    assert {"patients.created", "patients.viewed", "patients.updated"}.issubset(actions)
