"""P10-S01: production configuration is validated at startup, secrets can come
from files, and the HTTP layer enforces the production topology (HTTPS behind a
trusted proxy, same-origin writes, request limits)."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core.config import Settings
from app.core.http_security import (
    HttpsOnlyMiddleware,
    RequestSizeLimitMiddleware,
    SameOriginWritesMiddleware,
    TrustedProxyMiddleware,
)
from tests.prod_settings import PROD, prod_kwargs

BACKEND = Path(__file__).resolve().parent.parent


# ------------------------------------------------------------ config validation


def test_a_complete_production_configuration_is_accepted():
    settings = Settings(**prod_kwargs())
    assert settings.cookie_secure is True
    assert settings.https_enforced is True


def test_local_environment_keeps_working_with_dev_defaults():
    settings = Settings(_env_file=None)
    assert settings.is_local and settings.cookie_secure is False and settings.https_enforced is False


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ({"jwt_access_secret_key": "local-dev-only-insecure-access-secret-change-me"}, "JWT_ACCESS_SECRET_KEY"),
        ({"jwt_refresh_secret_key": "short"}, "JWT_REFRESH_SECRET_KEY"),
        ({"qr_signing_secret_key": "a" * 40}, "QR_SIGNING_SECRET_KEY"),  # one repeated character
        ({"jwt_algorithm": "none"}, "JWT_ALGORITHM"),
        ({"access_token_expire_minutes": 600}, "ACCESS_TOKEN_EXPIRE_MINUTES"),
        ({"refresh_token_expire_days": 365}, "REFRESH_TOKEN_EXPIRE_DAYS"),
        ({"database_url": "postgresql+asyncpg://forahis:forahis@db.internal:5432/his"}, "DATABASE_URL"),
        ({"database_url": "postgresql+asyncpg://u:postgres@db.internal/his"}, "DATABASE_URL"),
        ({"database_url": "postgresql+asyncpg://u:Zq7-pT4mXw9LkR2vNc8@localhost/his"}, "DATABASE_URL"),
        ({"cors_origins": "http://his.example.com"}, "CORS_ORIGINS"),
        ({"cors_origins": "*"}, "CORS_ORIGINS"),
        ({"cors_origins": "https://localhost:3000"}, "CORS_ORIGINS"),
        ({"cors_origins": "https://his.example.com/app"}, "CORS_ORIGINS"),
        ({"cors_origins": ""}, "CORS_ORIGINS"),
        ({"public_base_url": ""}, "PUBLIC_BASE_URL"),
        ({"public_base_url": "http://his.example.com"}, "PUBLIC_BASE_URL"),
        ({"frontend_base_url": "http://his.example.com"}, "FRONTEND_BASE_URL"),
        ({"allowed_hosts": "*"}, "ALLOWED_HOSTS"),
        ({"allowed_hosts": ""}, "ALLOWED_HOSTS"),
        ({"allowed_hosts": "https://his.example.com"}, "ALLOWED_HOSTS"),
        ({"trusted_proxy_cidrs": ""}, "TRUSTED_PROXY_CIDRS"),
        ({"trusted_proxy_cidrs": "0.0.0.0/0"}, "TRUSTED_PROXY_CIDRS"),
        ({"trusted_proxy_cidrs": "not-a-cidr"}, "TRUSTED_PROXY_CIDRS"),
        ({"session_cookie_samesite": "sometimes"}, "SESSION_COOKIE_SAMESITE"),
        ({"cookie_domain": "https://his.example.com"}, "COOKIE_DOMAIN"),
        ({"rate_limit_enabled": False}, "RATE_LIMIT_ENABLED"),
        ({"debug": True}, "DEBUG"),
        ({"db_echo": True}, "DB_ECHO"),
        ({"seed_demo_data": True}, "SEED_DEMO_DATA"),
        ({"abdm_adapter": "production"}, "ABDM_CLIENT_ID"),
        ({"abdm_adapter": "gateway-9"}, "ABDM_ADAPTER"),
        ({"abdm_mock_simulate": "timeout"}, "ABDM_MOCK_SIMULATE"),
        ({"smtp_host": "smtp.example.com"}, "SMTP_FROM"),
        ({"smtp_username": "mailer"}, "SMTP_PASSWORD"),
        ({"file_storage_root": "./storage"}, "FILE_STORAGE_ROOT"),
        ({"max_request_body_bytes": 1024}, "MAX_REQUEST_BODY_BYTES"),
    ],
)
def test_each_unsafe_production_setting_stops_startup(override, expected):
    with pytest.raises(ValueError, match=expected):
        Settings(**prod_kwargs(**override))


def test_secrets_must_differ_from_each_other():
    shared = PROD["jwt_access_secret_key"]
    with pytest.raises(ValueError, match="must all differ"):
        Settings(**prod_kwargs(jwt_refresh_secret_key=shared))


def test_every_problem_is_reported_in_one_pass():
    with pytest.raises(ValueError) as caught:
        Settings(environment="production", _env_file=None)
    message = str(caught.value)
    for name in ("JWT_ACCESS_SECRET_KEY", "DATABASE_URL", "CORS_ORIGINS", "ALLOWED_HOSTS", "TRUSTED_PROXY_CIDRS"):
        assert name in message


def test_staging_is_held_to_the_production_standard():
    with pytest.raises(ValueError):
        Settings(environment="staging", _env_file=None)
    Settings(**prod_kwargs(environment="staging"))


def test_error_text_never_echoes_secret_values():
    with pytest.raises(ValueError) as caught:
        Settings(**prod_kwargs(jwt_access_secret_key="short-but-secret-123", database_url="postgresql+asyncpg://u:hunter2@db/x"))
    assert "short-but-secret-123" not in str(caught.value) and "hunter2" not in str(caught.value)


def test_startup_fails_in_a_real_process_with_unsafe_production_config():
    env = {k: v for k, v in os.environ.items() if k.upper() not in {n.upper() for n in PROD}}
    env.update(ENVIRONMENT="production", RATE_LIMIT_ENABLED="true", SEED_DEMO_DATA="false")
    result = subprocess.run(
        [sys.executable, "-c", "import app.main"], cwd=BACKEND, env=env, capture_output=True, text=True
    )
    assert result.returncode != 0
    assert "Unsafe configuration" in result.stderr


def test_startup_succeeds_in_a_real_process_with_a_safe_production_config():
    env = dict(os.environ)
    for key, value in PROD.items():
        env[key.upper()] = str(value)
    env.update(RATE_LIMIT_ENABLED="true", SEED_DEMO_DATA="false", DEBUG="false", DB_ECHO="false", ABDM_ADAPTER="mock")
    env.pop("ABDM_MOCK_SIMULATE", None)
    result = subprocess.run(
        [sys.executable, "-c", "import app.main; print('started')"], cwd=BACKEND, env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert "started" in result.stdout


# ---------------------------------------------------------------- secret files


def test_secrets_can_be_supplied_as_files(tmp_path):
    (tmp_path / "jwt_access_secret_key").write_text("file-supplied-access-secret-value-123456\n")
    (tmp_path / "smtp_password").write_text("mail-pass-from-file")
    settings = Settings(_env_file=None, _secrets_dir=str(tmp_path))
    assert settings.jwt_access_secret_key == "file-supplied-access-secret-value-123456"  # newline stripped
    assert settings.smtp_password.get_secret_value() == "mail-pass-from-file"
    assert "mail-pass-from-file" not in repr(settings)


def test_environment_beats_secret_files(tmp_path, monkeypatch):
    (tmp_path / "jwt_access_secret_key").write_text("from-file-" + "x" * 30)
    monkeypatch.setenv("JWT_ACCESS_SECRET_KEY", "from-env-" + "y" * 30)
    assert Settings(_env_file=None, _secrets_dir=str(tmp_path)).jwt_access_secret_key.startswith("from-env-")


def test_a_production_config_can_be_assembled_entirely_from_files(tmp_path):
    for key, value in PROD.items():
        if key not in {"environment", "debug"}:
            (tmp_path / key).write_text(str(value))
    settings = Settings(
        _env_file=None,
        _secrets_dir=str(tmp_path),
        environment="production",
        rate_limit_enabled=True,
        seed_demo_data=False,
        db_echo=False,
    )
    assert settings.jwt_access_secret_key == PROD["jwt_access_secret_key"]


# ------------------------------------------------------------------ middleware


async def _echo(request: Request):
    return JSONResponse(
        {"client": request.client.host if request.client else None, "scheme": request.url.scheme}
    )


def _app(*layers) -> Starlette:
    app = Starlette(
        routes=[
            Route("/api/v1/health", _echo, methods=["GET"]),
            Route("/echo", _echo, methods=["GET", "POST", "PUT", "PATCH", "DELETE"]),
        ]
    )
    for cls, kwargs in reversed(layers):  # first listed = outermost
        app.add_middleware(cls, **kwargs)
    return app


PROXY_NETS = Settings(_env_file=None, trusted_proxy_cidrs="172.16.0.0/12").trusted_proxy_networks


def _proxied_client(app, peer="172.18.0.5"):
    return TestClient(app, client=(peer, 50000), base_url="http://his.example.com")


def test_proxy_headers_are_honoured_only_from_a_trusted_peer():
    app = _app((TrustedProxyMiddleware, {"networks": PROXY_NETS}))
    headers = {"X-Forwarded-For": "203.0.113.9", "X-Forwarded-Proto": "https"}

    trusted = _proxied_client(app).get("/echo", headers=headers).json()
    assert trusted == {"client": "203.0.113.9", "scheme": "https"}

    stranger = _proxied_client(app, peer="198.51.100.7").get("/echo", headers=headers).json()
    assert stranger["client"] == "198.51.100.7" and stranger["scheme"] == "http"  # forged headers ignored


def test_a_client_cannot_prepend_a_fake_ip_to_x_forwarded_for():
    app = _app((TrustedProxyMiddleware, {"networks": PROXY_NETS}))
    # attacker sent "6.6.6.6"; the proxy appended the real peer 203.0.113.9
    response = _proxied_client(app).get("/echo", headers={"X-Forwarded-For": "6.6.6.6, 203.0.113.9"})
    assert response.json()["client"] == "203.0.113.9"


def test_chained_trusted_proxies_are_skipped():
    app = _app((TrustedProxyMiddleware, {"networks": PROXY_NETS}))
    response = _proxied_client(app).get("/echo", headers={"X-Forwarded-For": "203.0.113.9, 172.20.0.2"})
    assert response.json()["client"] == "203.0.113.9"


def test_plain_http_is_refused_but_health_checks_pass():
    app = _app((TrustedProxyMiddleware, {"networks": PROXY_NETS}), (HttpsOnlyMiddleware, {}))
    client = _proxied_client(app)

    refused = client.get("/echo")  # no X-Forwarded-Proto: http
    assert refused.status_code == 400 and refused.json()["error"]["code"] == "HTTPS_REQUIRED"
    assert client.get("/echo", headers={"X-Forwarded-Proto": "http"}).status_code == 400
    assert client.get("/echo", headers={"X-Forwarded-Proto": "https"}).status_code == 200
    assert client.get("/api/v1/health").status_code == 200  # container healthcheck


def test_an_untrusted_peer_cannot_claim_https():
    app = _app((TrustedProxyMiddleware, {"networks": PROXY_NETS}), (HttpsOnlyMiddleware, {}))
    response = _proxied_client(app, peer="198.51.100.7").get("/echo", headers={"X-Forwarded-Proto": "https"})
    assert response.status_code == 400


def test_oversized_bodies_are_rejected_by_declared_length():
    app = _app((RequestSizeLimitMiddleware, {"max_bytes": 1000}))
    client = TestClient(app)
    assert client.post("/echo", content=b"x" * 999).status_code == 200
    too_big = client.post("/echo", content=b"x" * 1001)
    assert too_big.status_code == 413 and too_big.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_oversized_chunked_bodies_without_a_length_are_rejected_too():
    async def read_body(request: Request):
        await request.body()
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/upload", read_body, methods=["POST"])])
    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=1000)
    client = TestClient(app)

    def chunks(total):
        for _ in range(total // 100):
            yield b"x" * 100

    assert client.post("/upload", content=chunks(900)).status_code == 200
    assert client.post("/upload", content=chunks(3000)).status_code == 413


TRUSTED = ["https://his.example.com"]


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_cross_origin_writes_are_rejected(method):
    app = _app((SameOriginWritesMiddleware, {"trusted_origins": TRUSTED}))
    client = TestClient(app, base_url="http://his.example.com")
    response = client.request(method, "/echo", headers={"Origin": "https://evil.example"})
    assert response.status_code == 403


def test_same_origin_trusted_origin_and_non_browser_writes_pass():
    app = _app((SameOriginWritesMiddleware, {"trusted_origins": TRUSTED}))
    client = TestClient(app, base_url="http://his.example.com")
    assert client.post("/echo", headers={"Origin": "http://his.example.com"}).status_code == 200  # same origin
    assert client.post("/echo", headers={"Origin": "https://his.example.com/"}).status_code == 200  # trusted list
    assert client.post("/echo").status_code == 200  # no Origin: not a browser request


def test_a_null_or_lookalike_origin_is_rejected():
    app = _app((SameOriginWritesMiddleware, {"trusted_origins": TRUSTED}))
    client = TestClient(app, base_url="http://his.example.com")
    for origin in ("null", "https://his.example.com.evil.example", "http://his.example.com:8080"):
        assert client.post("/echo", headers={"Origin": origin}).status_code == 403, origin


def test_reads_with_a_foreign_origin_are_not_blocked_by_the_write_guard():
    app = _app((SameOriginWritesMiddleware, {"trusted_origins": TRUSTED}))
    assert TestClient(app).get("/echo", headers={"Origin": "https://evil.example"}).status_code == 200


# ----------------------------------------------------- the real app, local mode


def test_real_app_rejects_cross_origin_login_posts(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "x", "password": "y"},
        headers={"Origin": "https://evil.example"},
    )
    assert response.status_code == 403


def test_real_app_accepts_the_configured_frontend_origin(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "wrong"},
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 401  # reached the handler


def test_real_app_caps_request_bodies(client):
    response = client.post("/api/v1/auth/login", content=b"x" * (7 * 1024 * 1024))
    assert response.status_code == 413
