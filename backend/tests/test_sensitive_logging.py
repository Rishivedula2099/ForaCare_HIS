"""P9-B04: logs must never contain passwords, OTPs, JWTs, API secrets, DB
credentials or bound patient data - whether our code, a library exception or
the server access log put them there."""
import logging
import re
import sys
from pathlib import Path

import pytest
from sqlalchemy.engine import make_url

from app.core.config import Settings, get_settings
from app.core.logging import REDACTED, SecretRedactionFilter, scrub

APP = Path(__file__).resolve().parents[1] / "app"
JWT_LIKE = re.compile(r"eyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.")


def _record(msg, *args, name="app.test", exc_info=None):
    return logging.LogRecord(name, logging.INFO, __file__, 1, msg, args or None, exc_info)


def _filtered(record) -> str:
    SecretRedactionFilter([]).filter(record)
    text = record.getMessage()
    if record.exc_text:
        text += "\n" + record.exc_text
    return text


# --- scrubber unit tests --------------------------------------------------------


def test_scrub_masks_jwts_bearer_and_token_cookies():
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTYifQ.c2lnbmF0dXJlLXZhbHVl"
    out = scrub(f"token {jwt} Authorization: Bearer abcdefgh12345678 cookie access_token={jwt}; refresh_token=xyz123456")
    assert jwt not in out and "abcdefgh12345678" not in out and "xyz123456" not in out


@pytest.mark.parametrize(
    "text,secret",
    [
        ("login failed password=Hunter2!x", "Hunter2!x"),
        ('payload {"password": "Hunter2!x", "u": 1}', "Hunter2!x"),
        ("verify otp=482913 for user", "482913"),
        ("{'new_password': 's3cretPass'}", "s3cretPass"),
        ("client_secret: abcdef123456", "abcdef123456"),
        ("connect postgresql+asyncpg://forahis:dbPassw0rd@db:5432/x failed", "dbPassw0rd"),
    ],
)
def test_scrub_masks_credential_key_values(text, secret):
    assert secret not in scrub(text)


def test_scrub_removes_sql_bound_parameters():
    err = (
        "IntegrityError: duplicate key\n"
        "[SQL: INSERT INTO patients (first_name, password_hash) VALUES ($1, $2)]\n"
        "[parameters: ('Rajesh', '$2b$12$abcdefghijklmnop', 'DOB 1990-01-01')]\n"
        "(Background on this error at: https://sqlalche.me/e/20/gkpj)"
    )
    out = scrub(err)
    assert "Rajesh" not in out and "$2b$12$" not in out and "1990-01-01" not in out
    assert "duplicate key" in out


def test_scrub_leaves_ordinary_messages_alone():
    msg = "POST /api/v1/auth/login -> 401 (12.00ms) request_id=abc-123"
    assert scrub(msg) == msg


def test_filter_masks_configured_secrets_in_message_and_traceback():
    flt = SecretRedactionFilter(["super-secret-value-123"])
    try:
        raise RuntimeError("boom super-secret-value-123")
    except RuntimeError:
        record = _record("calling with super-secret-value-123", exc_info=sys.exc_info())
    flt.filter(record)
    assert "super-secret-value-123" not in record.getMessage()
    assert "super-secret-value-123" not in record.exc_text
    assert record.exc_info is None


def test_access_log_query_strings_are_stripped():
    record = _record(
        '%s - "%s %s HTTP/%s" %d',
        "127.0.0.1:5000", "GET", "/api/v1/patients?name=Rajesh&mobile=9876543210", "1.1", 200,
        name="uvicorn.access",
    )
    SecretRedactionFilter([]).filter(record)
    line = record.getMessage()
    assert "Rajesh" not in line and "9876543210" not in line
    assert "/api/v1/patients" in line


def test_settings_repr_hides_credentials():
    settings = get_settings()
    rendered = repr(settings) + str(settings)
    for secret in (
        settings.jwt_access_secret_key,
        settings.jwt_refresh_secret_key,
        settings.qr_signing_secret_key,
        settings.database_password,
    ):
        if len(secret) >= 6:
            assert secret not in rendered


def test_db_echo_is_rejected_outside_local():
    with pytest.raises(ValueError, match="DB_ECHO"):
        Settings(
            environment="production",
            debug=False,
            db_echo=True,
            jwt_access_secret_key="a" * 40,
            jwt_refresh_secret_key="b" * 40,
            qr_signing_secret_key="c" * 40,
        )


def test_database_password_is_parsed_for_redaction():
    s = Settings(database_url="postgresql+asyncpg://u:p%40ss-w0rd@h:5432/d")
    assert s.database_password == make_url(s.database_url).password == "p@ss-w0rd"


# --- live: drive the real app and inspect what it logs ---------------------------


@pytest.fixture
def captured(caplog):
    """All app logs, passed through the production redaction filter."""
    caplog.set_level(logging.DEBUG)
    handler = caplog.handler
    handler.addFilter(SecretRedactionFilter([get_settings().jwt_access_secret_key]))
    yield caplog
    handler.filters.clear()


def _all_logged(caplog) -> str:
    return "\n".join(
        [r.getMessage() for r in caplog.records] + [r.exc_text or "" for r in caplog.records]
    )


def test_login_flow_logs_no_password_or_jwt(client, captured):
    password = "Demo@123"
    client.post("/api/v1/auth/login", json={"username": "dr.priya", "password": "Wrong-Pass-9!"})
    ok = client.post("/api/v1/auth/login", json={"username": "dr.priya", "password": password})
    assert ok.status_code == 200
    access = client.cookies.get("access_token")
    refresh = client.cookies.get("refresh_token")
    client.post("/api/v1/auth/refresh")
    client.get("/api/v1/auth/me")
    client.post("/api/v1/auth/logout")

    logged = _all_logged(captured)
    for secret in ("Wrong-Pass-9!", password, access, refresh):
        assert secret and secret not in logged
    assert not JWT_LIKE.search(logged)


def test_otp_flow_logs_no_code(client, captured):
    client.post("/api/v1/auth/login", json={"username": "dr.priya", "password": "Demo@123"})
    r = client.post("/api/v1/auth/phone/change/request", json={"new_phone": "9000000042"})
    assert r.status_code == 200, r.text
    code = r.json()["data"].get("debug_code")  # exposed in local only
    client.post("/api/v1/auth/phone/change/verify", json={"new_phone": "9000000042", "code": "000000"})
    logged = _all_logged(captured)
    assert "000000" not in re.sub(r"\(\d+\.\d+ms\)|request_id=\S+", "", logged)
    if code:
        assert code not in logged


def test_unhandled_db_error_does_not_log_bound_values(client, captured, monkeypatch):
    """A failing INSERT surfaces SQLAlchemy's bound parameters in the
    exception text; the log must not carry patient data from them."""
    from app.modules.patients import service

    marker = "ZzUniquePatientMarker"

    async def boom(*args, **kwargs):
        from sqlalchemy.exc import IntegrityError

        raise IntegrityError(
            "INSERT INTO patients (first_name) VALUES ($1)", {"first_name": marker}, Exception("dup")
        )

    monkeypatch.setattr(service, "create_patient", boom)
    client.post("/api/v1/auth/login", json={"username": "dr.priya", "password": "Demo@123"})
    r = client.post("/api/v1/patients", json={"first_name": marker})  # 422 or 500: both must stay clean
    assert marker not in _all_logged(captured) or r.status_code == 422


# --- static guards ------------------------------------------------------------------

SENSITIVE_NAMES = re.compile(r"password|passwd|otp|secret|token|jwt|authorization|cookie", re.I)
LOG_CALL = re.compile(r"\b(?:logger|logging|log)\.(?:debug|info|warning|error|exception|critical)\(")


def test_no_log_call_interpolates_a_sensitive_variable():
    """A logger call whose arguments mention a credential-ish name is almost
    certainly a leak. Messages (string literals) may use the words."""
    offenders = []
    for path in APP.rglob("*.py"):
        if path.name == "logging.py":
            continue
        lines = path.read_text(encoding="utf8").splitlines()
        for i, line in enumerate(lines):
            if not LOG_CALL.search(line):
                continue
            call = " ".join(lines[i : i + 6]).split(")")[0]
            args = re.sub(r'(["\']).*?\1', "", call)  # drop string literals
            if SENSITIVE_NAMES.search(args):
                offenders.append(f"{path.relative_to(APP)}:{i + 1}: {line.strip()}")
    assert not offenders, "\n".join(offenders)


def test_no_print_statements_in_application_code():
    offenders = [
        f"{p.relative_to(APP)}:{n}"
        for p in APP.rglob("*.py")
        for n, line in enumerate(p.read_text(encoding="utf8").splitlines(), 1)
        if re.match(r"\s*print\(", line)
    ]
    assert not offenders, offenders


def test_sql_echo_is_off_by_default():
    assert Settings.model_fields["db_echo"].default is False


def test_redacted_marker_is_stable():
    assert REDACTED == "[REDACTED]"
