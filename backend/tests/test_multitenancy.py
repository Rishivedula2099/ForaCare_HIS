SUPER_ADMIN = "super.admin"
HOSPITAL_ADMIN = "hospital.admin"
DOCTOR = "dr.priya"
SUNRISE_ADMIN = "sunrise.admin"
DEMO_PASSWORD = "Demo@123"


def _token(client, username: str, password: str = DEMO_PASSWORD) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    return response.json()["data"]["tokens"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_facilities_list_is_scoped_to_callers_tenant(client):
    token = _token(client, HOSPITAL_ADMIN)

    response = client.get("/api/v1/facilities", headers=_auth(token))

    assert response.status_code == 200
    facilities = response.json()["data"]
    assert len(facilities) >= 1
    assert all(f["tenant_id"] == facilities[0]["tenant_id"] for f in facilities)
    assert all(f["facility_code"].startswith("FC-") for f in facilities)


def test_facilities_list_forbidden_without_permission(client):
    token = _token(client, DOCTOR)

    response = client.get("/api/v1/facilities", headers=_auth(token))

    assert response.status_code == 403


def test_cannot_fetch_another_tenants_facility(client):
    sunrise_token = _token(client, SUNRISE_ADMIN)
    facilities = client.get("/api/v1/facilities", headers=_auth(sunrise_token)).json()["data"]
    sunrise_facility_id = facilities[0]["id"]

    foracare_admin_token = _token(client, HOSPITAL_ADMIN)
    response = client.get(
        f"/api/v1/facilities/{sunrise_facility_id}", headers=_auth(foracare_admin_token)
    )

    assert response.status_code == 404


def test_hospital_admin_can_create_and_update_own_tenant_facility(client):
    token = _token(client, HOSPITAL_ADMIN)

    create_response = client.post(
        "/api/v1/facilities",
        json={"name": "ForaCare Test Branch", "facility_code": "FC-TEST-99"},
        headers=_auth(token),
    )
    assert create_response.status_code == 200
    facility = create_response.json()["data"]
    assert facility["is_active"] is True

    update_response = client.patch(
        f"/api/v1/facilities/{facility['id']}",
        json={"is_active": False},
        headers=_auth(token),
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["is_active"] is False


def test_tenants_endpoint_requires_super_admin(client):
    hospital_admin_token = _token(client, HOSPITAL_ADMIN)
    forbidden = client.get("/api/v1/tenants", headers=_auth(hospital_admin_token))
    assert forbidden.status_code == 403

    super_admin_token = _token(client, SUPER_ADMIN)
    allowed = client.get("/api/v1/tenants", headers=_auth(super_admin_token))
    assert allowed.status_code == 200
    codes = {tenant["code"] for tenant in allowed.json()["data"]}
    assert {"FORACARE", "SUNRISE"}.issubset(codes)


def test_super_admin_can_fetch_any_tenant_by_id_unknown_id_is_404(client):
    super_admin_token = _token(client, SUPER_ADMIN)

    tenants = client.get("/api/v1/tenants", headers=_auth(super_admin_token)).json()["data"]
    sunrise_id = next(t["id"] for t in tenants if t["code"] == "SUNRISE")

    found = client.get(f"/api/v1/tenants/{sunrise_id}", headers=_auth(super_admin_token))
    assert found.status_code == 200
    assert found.json()["data"]["code"] == "SUNRISE"

    missing = client.get(
        "/api/v1/tenants/00000000-0000-0000-0000-000000000000", headers=_auth(super_admin_token)
    )
    assert missing.status_code == 404
