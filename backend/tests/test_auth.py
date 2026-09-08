VALID_USERNAME = "dr.priya"
VALID_PASSWORD = "Demo@123"


def _login(client, username: str = VALID_USERNAME, password: str = VALID_PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def test_login_returns_tokens_and_context_in_standard_envelope(client):
    response = _login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None

    data = body["data"]
    assert data["user"]["username"] == VALID_USERNAME
    assert data["user"]["role"]["code"] == "DOCTOR"
    assert "patients.view" in data["user"]["permissions"]
    assert data["tenant"]["code"] == "FORACARE"
    assert data["facility"]["facility_code"]
    assert data["tokens"]["access_token"]
    assert data["tokens"]["refresh_token"]
    assert data["tokens"]["token_type"] == "bearer"


# NOTE: sign-in is temporarily bypassed for local development (see the
# TODO in app/modules/auth/service.py::authenticate_user) - any password
# works for a known username, and an unknown username falls back to a
# seeded demo user rather than rejecting. These tests document that
# bypass; flip them back to expecting 401 once the bypass is removed.
def test_login_with_any_password_succeeds_for_known_user(client):
    response = _login(client, password="literally-anything")

    assert response.status_code == 200
    assert response.json()["data"]["user"]["username"] == VALID_USERNAME


def test_login_with_unknown_username_falls_back_to_demo_user(client):
    response = _login(client, username="does.not.exist", password="literally-anything")

    assert response.status_code == 200
    assert response.json()["data"]["user"]["username"] == VALID_USERNAME


def test_me_without_token_returns_401(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_with_valid_token_returns_current_user(client):
    access_token = _login(client).json()["data"]["tokens"]["access_token"]

    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["user"]["username"] == VALID_USERNAME


def test_me_with_garbage_token_returns_401(client):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})

    assert response.status_code == 401


def test_refresh_rotates_and_invalidates_old_refresh_token(client):
    tokens = _login(client).json()["data"]["tokens"]

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()["data"]
    assert new_tokens["access_token"] != tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401


def test_logout_revokes_refresh_token(client):
    tokens = _login(client).json()["data"]["tokens"]

    logout_response = client.post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert logout_response.status_code == 200

    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert reused.status_code == 401


def test_change_password_requires_correct_current_password(client):
    # Sign-in is bypassed, but change-password is not: it still verifies
    # the current password hash directly, independent of login.
    tokens = _login(client, username="auditor", password="anything-works-here").json()["data"]["tokens"]
    access_token = tokens["access_token"]

    wrong_current = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "not-the-real-password", "new_password": "NewDemo@456"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert wrong_current.status_code == 401

    change_response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Demo@123", "new_password": "NewDemo@456"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert change_response.status_code == 200

    # Restore original password so this test is repeatable across runs.
    client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "NewDemo@456", "new_password": "Demo@123"},
        headers={"Authorization": f"Bearer {access_token}"},
    )


def test_role_gated_dependency_blocks_wrong_role(client):
    from fastapi import APIRouter, Depends

    from app.core.permissions import require_roles
    from app.main import app
    from app.modules.rbac.constants import SystemRole

    probe_router = APIRouter()

    @probe_router.get("/test-only/super-admin-probe")
    async def _probe(_user=Depends(require_roles(SystemRole.SUPER_ADMIN))):
        return {"ok": True}

    app.include_router(probe_router)

    doctor_token = _login(client).json()["data"]["tokens"]["access_token"]
    forbidden = client.get(
        "/test-only/super-admin-probe", headers={"Authorization": f"Bearer {doctor_token}"}
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "FORBIDDEN"

    admin_token = _login(client, username="super.admin").json()["data"]["tokens"]["access_token"]
    allowed = client.get(
        "/test-only/super-admin-probe", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert allowed.status_code == 200
