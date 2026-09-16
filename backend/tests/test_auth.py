VALID_USERNAME = "dr.priya"
VALID_PASSWORD = "Demo@123"


def _login(client, username: str = VALID_USERNAME, password: str = VALID_PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def test_login_sets_httponly_cookies_and_returns_no_tokens_in_body(client):
    response = _login(client)

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None

    data = body["data"]
    assert data["user"]["username"] == VALID_USERNAME
    assert data["user"]["role"]["code"] == "DOCTOR"
    assert data["user"]["role"]["numeric_code"] == 3
    assert "patients.view" in data["user"]["permissions"]
    assert data["tenant"]["code"] == "FORACARE"
    assert data["facility"]["facility_code"]
    assert data["session"]["token_type"] == "bearer"
    assert data["session"]["expires_in"] == 15 * 60

    # No JWT should ever appear in the JSON body.
    assert "access_token" not in data
    assert "refresh_token" not in data

    access_cookie = response.cookies.get("access_token")
    refresh_cookie = response.cookies.get("refresh_token")
    assert access_cookie
    assert refresh_cookie

    set_cookie_headers = response.headers.get_list("set-cookie")
    access_header = next(h for h in set_cookie_headers if h.startswith("access_token="))
    refresh_header = next(h for h in set_cookie_headers if h.startswith("refresh_token="))
    assert "HttpOnly" in access_header
    assert "HttpOnly" in refresh_header
    assert "SameSite=lax" in access_header or "samesite=lax" in access_header.lower()


def test_login_with_wrong_password_returns_401(client):
    response = _login(client, password="not-the-real-password")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_login_with_unknown_username_returns_401(client):
    response = _login(client, username="does.not.exist", password="literally-anything")
    assert response.status_code == 401


def test_me_without_cookie_returns_401(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_me_with_valid_session_returns_current_user(client):
    _login(client)

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["user"]["username"] == VALID_USERNAME


def test_me_with_garbage_cookie_returns_401(client):
    client.cookies.set("access_token", "not-a-real-token")

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_refresh_rotates_and_reuse_of_old_refresh_cookie_is_detected(client):
    _login(client)
    old_refresh_cookie = client.cookies.get("refresh_token")
    old_access_cookie = client.cookies.get("access_token")

    refreshed = client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200

    new_refresh_cookie = client.cookies.get("refresh_token")
    new_access_cookie = client.cookies.get("access_token")
    assert new_refresh_cookie != old_refresh_cookie
    assert new_access_cookie != old_access_cookie

    # A valid session still works after rotation.
    assert client.get("/api/v1/auth/me").status_code == 200

    # Replaying the pre-rotation refresh token is reuse of an
    # already-rotated token: it must be rejected, and it must kill the
    # session entirely (not just the stale token).
    client.cookies.set("refresh_token", old_refresh_cookie)
    reused = client.post("/api/v1/auth/refresh")
    assert reused.status_code == 401

    # The whole session was revoked as a result - even the *new*,
    # otherwise-still-valid refresh token from the rotation above no
    # longer works.
    client.cookies.set("refresh_token", new_refresh_cookie)
    after_reuse = client.post("/api/v1/auth/refresh")
    assert after_reuse.status_code == 401


def test_logout_revokes_session_and_clears_cookies(client):
    _login(client)

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 200

    assert client.cookies.get("access_token") is None
    assert client.cookies.get("refresh_token") is None

    # Session is dead server-side too, not just cookie-cleared client-side.
    me_response = client.get("/api/v1/auth/me")
    assert me_response.status_code == 401


def test_change_password_requires_correct_current_password(client):
    _login(client, username="auditor")

    wrong_current = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "not-the-real-password", "new_password": "NewDemo@456"},
    )
    assert wrong_current.status_code == 401

    change_response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "Demo@123", "new_password": "NewDemo@456"},
    )
    assert change_response.status_code == 200

    # Restore original password so this test is repeatable across runs.
    client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "NewDemo@456", "new_password": "Demo@123"},
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

    _login(client)
    forbidden = client.get("/test-only/super-admin-probe")
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "FORBIDDEN"

    _login(client, username="super.admin")
    allowed = client.get("/test-only/super-admin-probe")
    assert allowed.status_code == 200


def test_email_change_requires_otp_verification(client):
    _login(client, username="nurse.mary")

    request_response = client.post(
        "/api/v1/auth/email/change/request", json={"new_email": "mary.joseph.new@foracare-his.com"}
    )
    assert request_response.status_code == 200
    debug_code = request_response.json()["data"]["debug_code"]
    assert debug_code and len(debug_code) == 6

    wrong_code = "111111" if debug_code != "111111" else "222222"
    wrong_response = client.post(
        "/api/v1/auth/email/change/verify",
        json={"new_email": "mary.joseph.new@foracare-his.com", "code": wrong_code},
    )
    assert wrong_response.status_code == 401

    verify_response = client.post(
        "/api/v1/auth/email/change/verify",
        json={"new_email": "mary.joseph.new@foracare-his.com", "code": debug_code},
    )
    assert verify_response.status_code == 200

    me = client.get("/api/v1/auth/me").json()["data"]
    assert me["user"]["email"] == "mary.joseph.new@foracare-his.com"
    assert me["user"]["email_verified"] is True

    # Restore original email so this test is repeatable across runs.
    restore_request = client.post(
        "/api/v1/auth/email/change/request", json={"new_email": "mary.joseph@foracare-his.com"}
    )
    restore_code = restore_request.json()["data"]["debug_code"]
    client.post(
        "/api/v1/auth/email/change/verify",
        json={"new_email": "mary.joseph@foracare-his.com", "code": restore_code},
    )


def test_email_change_otp_cannot_be_reused(client):
    _login(client, username="lab.tech")

    request_response = client.post(
        "/api/v1/auth/email/change/request", json={"new_email": "lab.tech.new@foracare-his.com"}
    )
    debug_code = request_response.json()["data"]["debug_code"]

    first = client.post(
        "/api/v1/auth/email/change/verify",
        json={"new_email": "lab.tech.new@foracare-his.com", "code": debug_code},
    )
    assert first.status_code == 200

    replay = client.post(
        "/api/v1/auth/email/change/verify",
        json={"new_email": "lab.tech.new@foracare-his.com", "code": debug_code},
    )
    assert replay.status_code == 401

    restore_request = client.post(
        "/api/v1/auth/email/change/request", json={"new_email": "lab.tech@foracare-his.com"}
    )
    restore_code = restore_request.json()["data"]["debug_code"]
    client.post(
        "/api/v1/auth/email/change/verify",
        json={"new_email": "lab.tech@foracare-his.com", "code": restore_code},
    )
