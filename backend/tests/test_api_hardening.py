"""P9-B01: cross-module API hardening - headers, rate limits, input bounds,
LIKE escaping, upload validation. DB-free where possible."""
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.core.rate_limit import check_rate_limit, reset_rate_limits
from app.core.sql import like_contains
from app.main import app
from app.modules.files import service as files_service


@pytest.fixture
def limits_on():
    settings = get_settings()
    previous = settings.rate_limit_enabled
    settings.rate_limit_enabled = True
    reset_rate_limits()
    yield
    settings.rate_limit_enabled = previous
    reset_rate_limits()


def test_security_headers_present():
    with TestClient(app) as c:
        r = c.get("/api/v1/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["cache-control"] == "no-store"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]


def test_hostile_request_id_is_replaced():
    with TestClient(app) as c:
        r = c.get("/api/v1/health", headers={"X-Request-ID": "abc def<script>"})
    assert r.headers["x-request-id"] != "abc def<script>"
    assert len(r.headers["x-request-id"]) == 36


def test_safe_request_id_is_echoed():
    with TestClient(app) as c:
        r = c.get("/api/v1/health", headers={"X-Request-ID": "req-123"})
    assert r.headers["x-request-id"] == "req-123"


def test_rate_limit_blocks_after_limit(limits_on):
    from fastapi import HTTPException

    for _ in range(3):
        check_rate_limit("t", limit=3, window_seconds=60)
    with pytest.raises(HTTPException) as exc:
        check_rate_limit("t", limit=3, window_seconds=60)
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


def test_login_rejects_oversized_password():
    with TestClient(app) as c:
        r = c.post("/api/v1/auth/login", json={"username": "u", "password": "x" * 5000})
    assert r.status_code == 422


def test_like_contains_escapes_metacharacters():
    bs = chr(92)
    assert like_contains("100%_a" + bs + "b") == "%100" + bs + "%" + bs + "_a" + bs * 2 + "b%"


def _image_bytes(fmt: str) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (4, 4)).save(buf, format=fmt)
    return buf.getvalue()


def test_upload_content_type_follows_real_format(tmp_path, monkeypatch):
    import uuid

    monkeypatch.setattr(get_settings(), "file_storage_root", str(tmp_path))
    ids = [uuid.uuid4() for _ in range(3)]
    path, content_type = files_service.validate_and_store_photo(
        tenant_id=ids[0], facility_id=ids[1], patient_id=ids[2],
        content_type="image/jpeg", raw_bytes=_image_bytes("PNG"),
    )
    assert content_type == "image/png" and path.endswith(".png")


def test_upload_rejects_non_image_and_empty(tmp_path, monkeypatch):
    import uuid

    monkeypatch.setattr(get_settings(), "file_storage_root", str(tmp_path))
    ids = [uuid.uuid4() for _ in range(3)]
    for payload in (b"<script>alert(1)</script>", b""):
        with pytest.raises(files_service.InvalidFileContentError):
            files_service.validate_and_store_photo(
                tenant_id=ids[0], facility_id=ids[1], patient_id=ids[2],
                content_type="image/png", raw_bytes=payload,
            )
