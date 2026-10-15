"""P8-B04 / P8-F04: integration secrets stay out of the repo, logs, reprs and
API responses."""
import logging
import re
import subprocess
from pathlib import Path

import pytest

from app.core.config import Settings
from app.core.logging import SecretRedactionFilter
from tests.prod_settings import prod_kwargs

REPO_ROOT = Path(__file__).resolve().parents[2]


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        pytest.skip("not a git checkout")
    return result.stdout.splitlines()


def test_no_env_file_is_tracked_except_the_example():
    env_files = [f for f in _tracked_files() if Path(f).name.startswith(".env")]
    assert all(Path(f).name.endswith(".example") for f in env_files), env_files


def test_env_example_has_no_abdm_credential_values():
    text = (REPO_ROOT / "backend" / ".env.example").read_text()
    for key in ("ABDM_CLIENT_ID", "ABDM_CLIENT_SECRET"):
        assert re.search(rf"^{key}=\s*$", text, re.MULTILINE), f"{key} must be blank in .env.example"


def test_frontend_never_references_abdm_credentials():
    offenders = []
    for path in (REPO_ROOT / "frontend" / "src").rglob("*"):
        if "__tests__" in path.parts:
            continue  # tests use fake leaked strings on purpose
        if path.suffix in {".ts", ".tsx"} and re.search(
            r"ABDM_CLIENT|NEXT_PUBLIC_ABDM|client_secret|clientSecret", path.read_text(encoding="utf-8")
        ):
            offenders.append(str(path))
    assert offenders == []


def test_settings_repr_masks_the_abdm_secret():
    settings = Settings(abdm_client_secret="super-secret-value-123", _env_file=None)
    assert "super-secret-value-123" not in repr(settings)
    assert "super-secret-value-123" not in str(settings.model_dump())


def test_non_local_environment_rejects_public_dev_secrets():
    with pytest.raises(ValueError, match="JWT_ACCESS_SECRET_KEY"):
        Settings(environment="production", _env_file=None)
    Settings(**prod_kwargs())


def test_redaction_filter_masks_configured_credentials(caplog):
    record = logging.LogRecord(
        "x", logging.INFO, __file__, 1, "token for %s failed", ("super-secret-value-123",), None
    )
    SecretRedactionFilter(["super-secret-value-123"]).filter(record)
    assert record.getMessage() == "token for [REDACTED] failed"


def test_otp_is_not_echoed_in_validation_errors():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.core.exceptions import register_exception_handlers
    from app.modules.abdm.schemas import VerifyRequest

    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/verify")
    async def verify(payload: VerifyRequest):
        return {}

    response = TestClient(app).post("/verify", json={"transaction_id": "t", "otp": "12ab56"})
    assert response.status_code == 422
    assert "12ab56" not in response.text
