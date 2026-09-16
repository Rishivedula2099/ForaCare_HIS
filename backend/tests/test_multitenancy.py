DEMO_PASSWORD = "Demo@123"

SUPER_ADMIN = "super.admin"
HOSPITAL_ADMIN = "hospital.admin"
DOCTOR = "dr.priya"
SUNRISE_ADMIN = "sunrise.admin"


def _login(client, username: str, password: str = DEMO_PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def test_facilities_list_is_scoped_to_callers_tenant(client):
    _login(client, HOSPITAL_ADMIN)

    response = client.get("/api/v1/facilities")

    assert response.status_code == 200
    facilities = response.json()["data"]
    assert len(facilities) >= 1
    assert all(f["tenant_id"] == facilities[0]["tenant_id"] for f in facilities)
    assert all(f["facility_code"].startswith("FC-") for f in facilities)


def test_facilities_list_forbidden_without_permission(client):
    _login(client, DOCTOR)

    response = client.get("/api/v1/facilities")

    assert response.status_code == 403


def test_cannot_fetch_another_tenants_facility(client):
    _login(client, SUNRISE_ADMIN)
    facilities = client.get("/api/v1/facilities").json()["data"]
    sunrise_facility_id = facilities[0]["id"]

    _login(client, HOSPITAL_ADMIN)
    response = client.get(f"/api/v1/facilities/{sunrise_facility_id}")

    assert response.status_code == 404


def test_hospital_admin_can_create_and_update_own_tenant_facility(client):
    import uuid

    _login(client, HOSPITAL_ADMIN)

    facility_code = f"FC-TEST-{uuid.uuid4().hex[:8].upper()}"
    create_response = client.post(
        "/api/v1/facilities",
        json={"name": "ForaCare Test Branch", "facility_code": facility_code},
    )
    assert create_response.status_code == 200
    facility = create_response.json()["data"]
    assert facility["is_active"] is True

    update_response = client.patch(
        f"/api/v1/facilities/{facility['id']}",
        json={"is_active": False},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["is_active"] is False


def test_tenants_endpoint_requires_super_admin(client):
    _login(client, HOSPITAL_ADMIN)
    forbidden = client.get("/api/v1/tenants")
    assert forbidden.status_code == 403

    _login(client, SUPER_ADMIN)
    allowed = client.get("/api/v1/tenants")
    assert allowed.status_code == 200
    codes = {tenant["code"] for tenant in allowed.json()["data"]}
    assert {"FORACARE", "SUNRISE"}.issubset(codes)


def test_super_admin_can_fetch_any_tenant_by_id_unknown_id_is_404(client):
    _login(client, SUPER_ADMIN)

    tenants = client.get("/api/v1/tenants").json()["data"]
    sunrise_id = next(t["id"] for t in tenants if t["code"] == "SUNRISE")

    found = client.get(f"/api/v1/tenants/{sunrise_id}")
    assert found.status_code == 200
    assert found.json()["data"]["code"] == "SUNRISE"

    missing = client.get("/api/v1/tenants/00000000-0000-0000-0000-000000000000")
    assert missing.status_code == 404
