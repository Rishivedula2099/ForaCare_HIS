DEMO_PASSWORD = "Demo@123"


def _login(client, username: str, password: str = DEMO_PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _token(client, username: str, password: str = DEMO_PASSWORD) -> str:
    return _login(client, username, password).json()["data"]["tokens"]["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_login_writes_an_audit_log_entry(client):
    login_response = _login(client, "auditor")
    assert login_response.status_code == 200
    user_id = login_response.json()["data"]["user"]["id"]

    auditor_token = login_response.json()["data"]["tokens"]["access_token"]
    logs = client.get(
        "/api/v1/audit/logs",
        params={"resource_type": "user", "actor_user_id": user_id},
        headers=_auth(auditor_token),
    ).json()["data"]

    assert any(log["action"] == "auth.login.succeeded" for log in logs)
    login_entries = [log for log in logs if log["action"] == "auth.login.succeeded"]
    assert login_entries[0]["actor_username"] == "auditor"
    assert login_entries[0]["request_id"]


def test_audit_logs_endpoint_requires_permission(client):
    token = _token(client, "dr.priya")
    response = client.get("/api/v1/audit/logs", headers=_auth(token))
    assert response.status_code == 403


def test_audit_logs_are_scoped_to_callers_tenant(client):
    sunrise_token = _token(client, "sunrise.admin")
    _login(client, "sunrise.admin")

    logs = client.get("/api/v1/audit/logs", headers=_auth(sunrise_token)).json()["data"]
    assert all(log["tenant_id"] for log in logs)

    auditor_token = _token(client, "auditor")
    other_tenant_logs = client.get("/api/v1/audit/logs", headers=_auth(auditor_token)).json()["data"]

    sunrise_tenant_id = logs[0]["tenant_id"]
    assert all(log["tenant_id"] != sunrise_tenant_id for log in other_tenant_logs)


def test_role_permission_update_records_before_and_after(client):
    super_admin_token = _token(client, "super.admin")

    roles = client.get("/api/v1/rbac/roles", headers=_auth(super_admin_token)).json()["data"]
    nurse_role_id = next(r["id"] for r in roles if r["code"] == "NURSE")

    role_detail = client.get(
        f"/api/v1/rbac/roles/{nurse_role_id}", headers=_auth(super_admin_token)
    ).json()["data"]
    original_permission_ids = [p["id"] for p in role_detail["permissions"]]

    permissions = client.get("/api/v1/rbac/permissions", headers=_auth(super_admin_token)).json()["data"]
    extra_permission = next(p for p in permissions if p["code"] == "roles.view")
    new_permission_ids = list({*original_permission_ids, extra_permission["id"]})

    update_response = client.patch(
        f"/api/v1/rbac/roles/{nurse_role_id}/permissions",
        json={"permission_ids": new_permission_ids},
        headers=_auth(super_admin_token),
    )
    assert update_response.status_code == 200

    logs = client.get(
        "/api/v1/audit/logs",
        params={"resource_type": "role"},
        headers=_auth(super_admin_token),
    ).json()["data"]
    role_update_entries = [log for log in logs if log["resource_id"] == nurse_role_id]
    assert role_update_entries
    latest = role_update_entries[0]
    assert latest["before"]["permission_codes"] is not None
    assert latest["after"]["permission_codes"] is not None
    assert latest["before"] != latest["after"]

    # Restore original permissions so this test is repeatable across runs.
    client.patch(
        f"/api/v1/rbac/roles/{nurse_role_id}/permissions",
        json={"permission_ids": original_permission_ids},
        headers=_auth(super_admin_token),
    )
