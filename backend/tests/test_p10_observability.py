"""P10-S02: structured logs, correlation ids, readiness, metrics, abnormal-auth
detection and actionable error reporting - none of it exposing patient or
credential data."""
import json
import logging
import re
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core import alerting, metrics, readiness
from app.core.config import get_settings
from app.core.logging import JsonFormatter, RequestIdFilter, SecretRedactionFilter, log_event
from app.core.security_monitor import AuthActivityMonitor, monitor, pseudonym
from app.main import app

DEMO = "Demo@123"
JWT = re.compile(r"eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]*")


@pytest.fixture(autouse=True)
def clean_state():
    metrics.reset()
    monitor.reset()
    alerting.reset()
    readiness._last_state.clear()
    yield
    metrics.reset()
    monitor.reset()
    alerting.reset()
    readiness._last_state.clear()


class Capture(logging.Handler):
    """Collects records AND their final JSON rendering, exactly as production emits them."""

    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.addFilter(RequestIdFilter())
        self.addFilter(SecretRedactionFilter([]))
        self.setFormatter(JsonFormatter())
        self.lines: list[dict] = []
        self.raw: list[str] = []

    def emit(self, record):
        rendered = self.format(record)
        self.raw.append(rendered)
        self.lines.append(json.loads(rendered))

    def events(self, name):
        return [line for line in self.lines if line.get("event") == name]


@pytest.fixture()
def logs():
    handler = Capture()
    root = logging.getLogger()
    previous = root.level
    root.setLevel(logging.DEBUG)
    root.addHandler(handler)
    yield handler
    root.removeHandler(handler)
    root.setLevel(previous)


def login(client, username, password=DEMO):
    client.cookies.clear()
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


# ======================================================================= structured logs


def test_every_request_writes_one_structured_access_line(client, logs):
    client.cookies.clear()
    response = client.get("/api/v1/patients?name=Jane+Doe&mobile=9876543210")
    lines = logs.events("http_request")
    assert len(lines) == 1
    line = lines[0]
    assert line["http_method"] == "GET"
    assert line["path"] == "/api/v1/patients"  # the route template, no query string
    assert line["status"] == 401 == response.status_code
    assert line["request_id"] == response.headers["X-Request-ID"]
    assert isinstance(line["duration_ms"], (int, float))
    assert "timestamp" in line and line["level"] == "INFO"
    for secret in ("Jane", "9876543210", "name=", "mobile="):
        assert secret not in logs.raw[-1], secret


def test_the_access_line_names_the_authenticated_actor_by_id_only(client, logs):
    me = login(client, "dr.priya").json()["data"]
    client.get("/api/v1/auth/me")
    line = [l for l in logs.events("http_request") if l["path"] == "/api/v1/auth/me"][0]
    assert line["user_id"] == me["user"]["id"]
    assert line["tenant_id"] == me["tenant"]["id"]
    assert line["facility_id"] == me["facility"]["id"]
    # identifiers, not identities: no name, username or email in any line
    blob = " ".join(logs.raw)
    for personal in ("Priya", "dr.priya", "priya.raman@"):
        assert personal not in blob, personal


def test_concrete_ids_never_appear_in_the_path_field(client, logs):
    patient_id = str(uuid.uuid4())
    login(client, "dr.priya")
    client.get(f"/api/v1/patients/{patient_id}")
    line = [l for l in logs.events("http_request") if "patients" in l["path"]][-1]
    assert line["path"] == "/api/v1/patients/{patient_id}"
    assert patient_id not in " ".join(logs.raw)


def test_credentials_and_tokens_never_reach_the_logs(client, logs):
    password = "Sup3r-Secret-Pa55!"
    login(client, "nobody.here", password)  # failed
    login(client, "dr.priya")  # succeeded: sets token cookies
    client.post("/api/v1/auth/change-password", json={"current_password": "wrong-current-1", "new_password": "N3w-Passw0rd!x"})
    blob = " ".join(logs.raw)
    assert password not in blob and "wrong-current-1" not in blob and "N3w-Passw0rd" not in blob
    assert not JWT.search(blob)
    assert "access_token=" not in blob and "refresh_token=" not in blob


def test_log_event_scrubs_string_fields_as_defence_in_depth(logs):
    log_event(logging.getLogger("t"), logging.INFO, "probe", note="password=hunter2 Bearer abcdefghijklmnop", count=3)
    line = logs.events("probe")[0]
    assert "hunter2" not in logs.raw[-1] and "abcdefghijklmnop" not in logs.raw[-1]
    assert line["count"] == 3


def test_a_field_cannot_overwrite_core_log_keys(logs):
    # (log_event's own parameters make `level`/`event` unusable as field names; a raw
    # `extra` dict is the way a stray field could try to shadow a core key.)
    logging.getLogger("t").info(
        "probe2", extra={"event": "probe2", "fields": {"level": "FAKE", "request_id": "forged", "timestamp": "x"}}
    )
    line = logs.events("probe2")[0]
    assert line["level"] == "INFO" and line["request_id"] != "forged"


def test_health_probe_successes_are_quiet_but_failures_are_not(client, logs, monkeypatch):
    client.get("/api/v1/health")
    quiet = logs.events("http_request")[-1]
    assert quiet["level"] == "DEBUG"
    client.get("/api/v1/health/does-not-exist")
    assert logs.events("http_request")[-1]["level"] == "INFO"  # a 404 is not quiet


# ============================================================================ correlation ids


def test_request_id_is_echoed_in_headers_and_every_error_body(client):
    client.cookies.clear()
    for path, method, kwargs in (
        ("/api/v1/does-not-exist", "get", {}),
        ("/api/v1/patients", "get", {}),  # 401
        ("/api/v1/auth/login", "post", {"json": {"username": ""}}),  # 422
    ):
        response = getattr(client, method)(path, headers={"X-Request-ID": "trace-abc-123"}, **kwargs)
        assert response.headers["X-Request-ID"] == "trace-abc-123"
        assert response.json()["meta"]["request_id"] == "trace-abc-123", path


def test_a_hostile_request_id_is_replaced_before_it_can_reach_the_logs(client, logs):
    client.get("/api/v1/health/nothing", headers={"X-Request-ID": "x\nforged-line {\"level\":\"CRITICAL\"}"})
    assert all(line["level"] != "CRITICAL" for line in logs.lines)
    assert all("forged-line" not in raw for raw in logs.raw)


# ===================================================================== error reporting


@pytest.fixture()
def boom_route():
    from fastapi import APIRouter

    router = APIRouter()

    @router.get("/api/v1/_test/boom")
    async def boom():
        raise RuntimeError("db exploded password=hunter2 Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ4In0.c2ln")

    @router.get("/api/v1/_test/boom-value")
    async def boom_value():
        raise ValueError("a different failure")

    # The dev .env has DEBUG=true, which makes Starlette answer with its traceback page
    # instead of our handler. Production refuses DEBUG, so test the production behaviour.
    was_debug = app.debug
    app.debug = False
    app.middleware_stack = None  # rebuilt on the next request with debug off
    app.include_router(router)
    yield
    app.router.routes[:] = [r for r in app.router.routes if not getattr(r, "path", "").startswith("/api/v1/_test/")]
    app.debug = was_debug
    app.middleware_stack = None


def test_an_unhandled_error_is_reported_with_a_reference_and_no_cause(boom_route, logs):
    with TestClient(app, raise_server_exceptions=False) as c:
        response = c.get("/api/v1/_test/boom")
    assert response.status_code == 500
    body = response.json()
    rid = body["meta"]["request_id"]
    assert rid and response.headers["X-Request-ID"] == rid  # even a 500 is traceable
    assert rid in body["error"]["message"]  # the user can quote it
    assert "exploded" not in response.text and "hunter2" not in response.text and "RuntimeError" not in response.text

    event = logs.events("unhandled_exception")[0]
    assert event["request_id"] == rid
    assert event["error_type"] == "RuntimeError"
    assert re.fullmatch(r"[0-9a-f]{12}", event["error_fingerprint"])
    assert event["route"] == "/api/v1/_test/boom" and event["http_method"] == "GET"
    assert event["level"] == "ERROR"
    # the traceback is present for the engineer but scrubbed of secrets
    full = logs.raw[logs.lines.index(event)]
    assert "RuntimeError" in event.get("exception", "")
    assert "hunter2" not in full and not JWT.search(full)
    # and the access line for that request is a 500, not lost
    assert [l for l in logs.events("http_request") if l["status"] == 500]


def test_fingerprints_group_the_same_bug_and_separate_different_ones(boom_route):
    with TestClient(app, raise_server_exceptions=False) as c:
        for _ in range(2):
            c.get("/api/v1/_test/boom")
        c.get("/api/v1/_test/boom-value")
    assert metrics.counter_value("his_unhandled_exceptions_total") == 3
    from app.core.exceptions import error_fingerprint

    def raised(exc):
        try:
            raise exc
        except Exception as caught:  # noqa: BLE001
            return error_fingerprint(caught)

    assert raised(RuntimeError("one")) == raised(RuntimeError("two"))  # message is not part of the identity
    assert raised(RuntimeError("one")) != raised(ValueError("one"))


def test_handled_server_errors_are_logged_at_error_and_counted(client, logs, monkeypatch):
    async def down():
        return False

    import app.api.v1.health as health_api

    monkeypatch.setattr(health_api, "check_database_connection", down)
    response = client.get("/api/v1/health/db")
    assert response.status_code == 503
    event = logs.events("app_error")[-1]
    assert event["level"] == "ERROR" and event["code"] == "DATABASE_UNAVAILABLE"
    assert metrics.counter_value("his_server_errors_total", {"code": "DATABASE_UNAVAILABLE"}) == 1


def test_client_errors_are_warnings_not_errors(client, logs):
    login(client, "dr.priya")
    client.get("/api/v1/facilities")  # 403
    assert logs.events("app_error")[-1]["level"] == "WARNING"
    assert metrics.counter_total("his_server_errors_total") == 0


def test_error_alerts_go_to_the_webhook_once_per_bug_and_carry_no_cause(boom_route, monkeypatch):
    sent: list[dict] = []

    class FakeResponse:
        status_code = 200

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, json):
            sent.append({"url": url, **json})
            return FakeResponse()

    monkeypatch.setattr(alerting.httpx, "AsyncClient", FakeClient)
    settings = get_settings()
    monkeypatch.setattr(settings, "alert_webhook_url", type(settings.alert_webhook_url)("https://hooks.example.org/T0K3N"))
    with TestClient(app, raise_server_exceptions=False) as c:
        for _ in range(3):
            c.get("/api/v1/_test/boom")
        deadline = time.time() + 3
        while not sent and time.time() < deadline:
            time.sleep(0.05)
    assert len(sent) == 1  # cooldown: three failures, one message
    text_ = sent[0]["text"]
    assert "RuntimeError" in text_ and "/api/v1/_test/boom" in text_ and "request_id=" in text_
    assert "hunter2" not in text_ and "exploded" not in text_ and "eyJ" not in text_


def test_alerting_is_silent_without_a_webhook_and_survives_a_dead_one(boom_route, monkeypatch):
    import asyncio

    assert asyncio.run(alerting.send_alert("k", "nothing configured")) is False
    settings = get_settings()
    monkeypatch.setattr(settings, "alert_webhook_url", type(settings.alert_webhook_url)("https://127.0.0.1:1/dead"))
    assert asyncio.run(alerting.send_alert("k2", "dead endpoint")) is False  # never raises
    with TestClient(app, raise_server_exceptions=False) as c:
        assert c.get("/api/v1/_test/boom").status_code == 500  # the request itself is unaffected


# ============================================================================= readiness


def test_liveness_is_minimal_and_hides_the_environment_name_outside_local(client, monkeypatch):
    local = client.get("/api/v1/health").json()["data"]
    assert local["status"] == "ok" and local["environment"] == "local"
    monkeypatch.setattr(get_settings(), "environment", "production")
    data = client.get("/api/v1/health").json()["data"]
    assert data["status"] == "ok" and "environment" not in data


def test_readiness_passes_when_database_schema_and_storage_are_healthy(client):
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    assert body["status"] == "ready"
    assert body["checks"] == {"database": {"status": "ok"}, "migrations": {"status": "ok"}, "storage": {"status": "ok"}}
    assert metrics.render().count('his_ready{check="database"} 1') == 1


def test_readiness_fails_503_when_the_database_is_unreachable_without_leaking_why(client, logs, monkeypatch):
    class Dead:
        def connect(self):
            raise ConnectionRefusedError("could not connect to postgresql://his_app:S3cretP4ss@db.internal:5432/his")

    monkeypatch.setattr(readiness, "engine", Dead())
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "NOT_READY"
    assert body["data"]["checks"]["database"] == {"status": "fail", "reason": "unreachable"}
    assert "S3cretP4ss" not in response.text and "db.internal" not in response.text
    assert "S3cretP4ss" not in " ".join(logs.raw)  # nor in the log's traceback
    assert metrics.render().count('his_ready{check="database"} 0') == 1


def test_readiness_fails_when_the_schema_is_behind_the_code(client, monkeypatch):
    monkeypatch.setattr(readiness, "code_head_revision", lambda: "ffffffffffff")
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json()["data"]["checks"]["migrations"]["reason"] == "behind_head"


def test_readiness_fails_when_storage_is_not_writable(client, tmp_path, monkeypatch):
    blocker = tmp_path / "a-file"
    blocker.write_text("x")
    monkeypatch.setattr(get_settings(), "file_storage_root", str(blocker / "uploads"))  # cannot mkdir under a file
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json()["data"]["checks"]["storage"] == {"status": "fail", "reason": "not_writable"}
    assert str(tmp_path) not in response.text


def test_readiness_fails_when_the_storage_volume_is_nearly_full(client, tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "file_storage_root", str(tmp_path))
    monkeypatch.setattr(settings, "storage_min_free_mb", 10**9)  # more free space than any disk has
    response = client.get("/api/v1/health/ready")
    assert response.json()["data"]["checks"]["storage"]["reason"] == "low_disk"
    assert not list(tmp_path.glob(".readiness-*"))  # the probe cleans up after itself


def test_readiness_failures_are_logged_once_per_state_change_not_per_probe(client, logs, monkeypatch):
    monkeypatch.setattr(readiness, "code_head_revision", lambda: "ffffffffffff")
    for _ in range(5):
        client.get("/api/v1/health/ready")
    assert len(logs.events("readiness_failed")) == 1
    monkeypatch.undo()
    client.get("/api/v1/health/ready")
    assert len(logs.events("readiness_recovered")) == 1


# ================================================================================ metrics


def test_metrics_expose_request_counts_and_latency_by_route_template(client):
    client.get("/api/v1/health")
    login(client, "dr.priya")
    patient_id = str(uuid.uuid4())
    client.get(f"/api/v1/patients/{patient_id}")
    text_ = client.get("/internal/metrics").text
    assert 'his_http_requests_total{method="GET",route="/api/v1/health",status="2xx"}' in text_
    assert 'route="/api/v1/patients/{patient_id}"' in text_
    assert "his_http_request_duration_seconds_bucket" in text_
    assert patient_id not in text_  # no identifier ever becomes a label


def test_metrics_labels_never_contain_users_ips_or_credentials(client):
    login(client, "someone.private", "Sup3r-Secret-Pa55!")
    text_ = client.get("/internal/metrics").text
    for forbidden in ("someone.private", "Sup3r", "testclient", "127.0.0.1"):
        assert forbidden not in text_


def test_authentication_events_are_counted(client):
    login(client, "nobody", "wrong-password-1")
    login(client, "dr.priya")
    client.get("/api/v1/facilities")  # permission denied
    client.post("/api/v1/auth/logout")
    text_ = client.get("/internal/metrics").text
    for event in ("login_failed", "login_succeeded", "permission_denied", "logout"):
        assert f'his_auth_events_total{{event="{event}"}} 1' in text_, event


def test_cross_tenant_access_attempts_are_counted(client):
    login(client, "sunrise.admin")
    foreign = client.get("/api/v1/facilities").json()["data"][0]["id"]
    login(client, "hospital.admin")
    assert client.get(f"/api/v1/facilities/{foreign}").status_code == 404
    assert 'his_auth_events_total{event="cross_tenant_access"} 1' in client.get("/internal/metrics").text


def test_rate_limited_requests_are_counted(client):
    settings = get_settings()
    settings.rate_limit_enabled = True
    try:
        from app.core.rate_limit import reset_rate_limits

        reset_rate_limits()
        for _ in range(settings.rate_limit_login_per_minute + 2):
            client.post("/api/v1/auth/login", json={"username": "rl.user", "password": "x"})
    finally:
        settings.rate_limit_enabled = False
        reset_rate_limits()
    assert 'his_rate_limited_total{scope="login-user"}' in client.get("/internal/metrics").text


def test_metrics_endpoint_does_not_exist_in_production_until_a_token_is_configured(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "environment", "production")
    assert client.get("/internal/metrics").status_code == 404
    monkeypatch.setattr(settings, "metrics_token", type(settings.metrics_token)("s3cr3t-scrape-token"))
    assert client.get("/internal/metrics").status_code == 401
    assert client.get("/internal/metrics", headers={"Authorization": "Bearer wrong"}).status_code == 401
    ok = client.get("/internal/metrics", headers={"Authorization": "Bearer s3cr3t-scrape-token"})
    assert ok.status_code == 200 and "his_app_info" in ok.text


def test_metrics_are_not_published_through_the_public_proxy():
    from pathlib import Path

    template = (Path(__file__).resolve().parents[2] / "infra" / "nginx" / "prod" / "default.conf.template").read_text()
    assert "location /internal/ { return 404; }" in template


# ========================================================= abnormal authentication activity


def _settings(**overrides):
    s = get_settings()
    return {k: getattr(s, k) for k in overrides} | overrides


def test_many_failed_logins_from_one_ip_raise_a_single_alert(logs):
    m = AuthActivityMonitor()
    threshold = get_settings().auth_alert_failed_logins_per_ip
    raised = []
    for i in range(threshold + 5):
        raised += m.record_login_failure("203.0.113.9", "alice")  # one user, so only the per-IP rule can fire first
    types = [a.type for a in raised]
    assert types.count("failed_logins_per_ip") == 1  # once, not on every later failure
    assert metrics.counter_value("his_security_alerts_total", {"type": "failed_logins_per_ip"}) == 1
    event = logs.events("security_alert")
    assert event and event[0]["level"] == "ERROR"


def test_trying_many_usernames_from_one_ip_is_credential_stuffing():
    m = AuthActivityMonitor()
    n = get_settings().auth_alert_distinct_users_per_ip
    raised = []
    for i in range(n):
        raised += m.record_login_failure("198.51.100.4", f"user{i}")
    assert [a.type for a in raised] == ["many_usernames_per_ip"]


def test_repeated_failures_against_one_account_from_many_ips_raise_an_alert():
    m = AuthActivityMonitor()
    n = get_settings().auth_alert_failed_logins_per_user
    raised = []
    for i in range(n):
        raised += m.record_login_failure(f"192.0.2.{i}", "victim")  # distributed guessing
    assert [a.type for a in raised] == ["failed_logins_per_user"]


def test_ordinary_typos_do_not_alert():
    m = AuthActivityMonitor()
    assert m.record_login_failure("192.0.2.1", "alice") == []
    assert m.record_login_failure("192.0.2.1", "alice") == []
    assert m.record_login_failure("192.0.2.2", "bob") == []


def test_alerts_use_a_pseudonym_never_the_attempted_username(logs):
    m = AuthActivityMonitor()
    n = get_settings().auth_alert_failed_logins_per_user
    for i in range(n):
        m.record_login_failure(f"192.0.2.{i}", "Hunter2-typed-as-username")
    blob = " ".join(logs.raw)
    assert "Hunter2" not in blob
    assert pseudonym("Hunter2-typed-as-username") in blob
    assert pseudonym("HUNTER2-typed-as-username ") == pseudonym("hunter2-typed-as-username")


def test_the_window_expires_old_failures(monkeypatch):
    m = AuthActivityMonitor()
    clock = {"t": 1000.0}
    monkeypatch.setattr("app.core.security_monitor.time.monotonic", lambda: clock["t"])
    n = get_settings().auth_alert_failed_logins_per_user
    for _ in range(n - 1):
        m.record_login_failure("192.0.2.1", "slow")
    clock["t"] += get_settings().auth_alert_window_seconds + 1
    assert m.record_login_failure("192.0.2.1", "slow") == []  # earlier attempts aged out


def test_an_alert_can_fire_again_in_a_later_window(monkeypatch):
    m = AuthActivityMonitor()
    clock = {"t": 5000.0}
    monkeypatch.setattr("app.core.security_monitor.time.monotonic", lambda: clock["t"])
    n = get_settings().auth_alert_failed_logins_per_user
    first = [a for _ in range(n) for a in m.record_login_failure("192.0.2.1", "again")]
    clock["t"] += get_settings().auth_alert_window_seconds + 5
    second = [a for _ in range(n) for a in m.record_login_failure("192.0.2.1", "again")]
    assert len(first) == 1 and len(second) == 1


def test_a_burst_of_permission_denials_by_one_user_is_flagged():
    m = AuthActivityMonitor()
    uid = str(uuid.uuid4())
    raised = []
    for _ in range(12):
        raised += m.record_permission_denied(uid)
    assert [a.type for a in raised] == ["permission_denied_burst"]


def test_a_failed_login_flood_through_the_api_alerts_and_is_audited(client, logs):
    n = get_settings().auth_alert_failed_logins_per_user
    username = f"flood.{uuid.uuid4().hex[:8]}"
    for _ in range(n):
        client.post("/api/v1/auth/login", json={"username": username, "password": "wrong-password-1"})
    assert metrics.counter_value("his_security_alerts_total", {"type": "failed_logins_per_user"}) == 1
    assert username not in " ".join(logs.raw)

    import asyncio

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    async def audited():
        engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
        try:
            async with async_sessionmaker(engine, class_=AsyncSession)() as db:
                row = await db.execute(
                    text(
                        "SELECT after FROM audit_logs WHERE action = 'security.abnormal_auth_activity' "
                        "AND after->>'subject' = :s ORDER BY created_at DESC LIMIT 1"
                    ),
                    {"s": pseudonym(username)},
                )
                found = row.first()
                await db.execute(text("DELETE FROM audit_logs WHERE after->>'subject' = :s"), {"s": pseudonym(username)})
                await db.execute(text("DELETE FROM audit_logs WHERE actor_username = :u"), {"u": username})
                await db.commit()
                return found
        finally:
            await engine.dispose()

    found = asyncio.run(audited())
    assert found is not None and found[0]["type"] == "failed_logins_per_user"


def test_refresh_token_reuse_raises_a_security_alert(client, logs):
    login(client, "dr.priya")
    old_refresh = client.cookies.get("refresh_token")
    assert client.post("/api/v1/auth/refresh").status_code == 200  # rotates
    client.cookies.set("refresh_token", old_refresh)
    assert client.post("/api/v1/auth/refresh").status_code == 401  # replay of the old one
    assert metrics.counter_value("his_security_alerts_total", {"type": "refresh_token_reuse"}) == 1
    assert 'his_auth_events_total{event="refresh_token_reuse"} 1' in client.get("/internal/metrics").text
    assert logs.events("security_alert")[-1]["alert_type"] == "refresh_token_reuse"


def test_route_templates_always_carry_the_api_prefix(client, logs):
    """Found on the production stack (newer pinned FastAPI): nested routers reported
    '/auth/login' without '/api/v1', which split metrics and broke log searches."""
    client.cookies.clear()
    client.post("/api/v1/auth/login", json={"username": "nobody.at.all", "password": "pw"})
    client.get(f"/api/v1/patients/{uuid.uuid4()}")
    paths = {line["path"] for line in logs.events("http_request")}
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/patients/{patient_id}" in paths
    assert "/auth/login" not in paths
