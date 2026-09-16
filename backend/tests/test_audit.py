DEMO_PASSWORD = "Demo@123"


def _login(client, username: str, password: str = DEMO_PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def test_login_writes_an_audit_log_entry(client):
    login_response = _login(client, "auditor")
    assert login_response.status_code == 200
    user_id = login_response.json()["data"]["user"]["id"]

    logs = client.get(
        "/api/v1/audit/logs",
        params={"resource_type": "user", "actor_user_id": user_id},
    ).json()["data"]

    assert any(log["action"] == "auth.login.succeeded" for log in logs)
    login_entries = [log for log in logs if log["action"] == "auth.login.succeeded"]
    assert login_entries[0]["actor_username"] == "auditor"
    assert login_entries[0]["request_id"]


def test_audit_logs_endpoint_requires_permission(client):
    _login(client, "dr.priya")
    response = client.get("/api/v1/audit/logs")
    assert response.status_code == 403


def test_audit_logs_are_scoped_to_callers_tenant(client):
    _login(client, "sunrise.admin")

    logs = client.get("/api/v1/audit/logs").json()["data"]
    assert all(log["tenant_id"] for log in logs)
    sunrise_tenant_id = logs[0]["tenant_id"]

    _login(client, "auditor")
    other_tenant_logs = client.get("/api/v1/audit/logs").json()["data"]

    assert all(log["tenant_id"] != sunrise_tenant_id for log in other_tenant_logs)


def test_role_permission_update_records_before_and_after(client):
    _login(client, "super.admin")

    roles = client.get("/api/v1/rbac/roles").json()["data"]
    nurse_role_id = next(r["id"] for r in roles if r["code"] == "NURSE")

    role_detail = client.get(f"/api/v1/rbac/roles/{nurse_role_id}").json()["data"]
    original_permission_ids = [p["id"] for p in role_detail["permissions"]]

    permissions = client.get("/api/v1/rbac/permissions").json()["data"]
    extra_permission = next(p for p in permissions if p["code"] == "roles.view")
    new_permission_ids = list({*original_permission_ids, extra_permission["id"]})

    update_response = client.patch(
        f"/api/v1/rbac/roles/{nurse_role_id}/permissions",
        json={"permission_ids": new_permission_ids},
    )
    assert update_response.status_code == 200

    logs = client.get(
        "/api/v1/audit/logs",
        params={"resource_type": "role"},
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
    )
