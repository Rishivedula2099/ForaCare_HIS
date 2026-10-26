"""P10-S02: readiness checks - "can this instance serve traffic correctly?".

Liveness (`GET /api/v1/health`) only says the process is up. Readiness
(`GET /api/v1/health/ready`) verifies what a request actually needs:

* database  - reachable, answers within a few seconds
* migrations - the schema is at the code's Alembic head (a half-migrated
               database is a failure, not a warning)
* storage   - the upload volume is writable and has free space

Each check reports `ok` / `fail` with a short reason CODE (`unreachable`,
`behind_head`, `not_writable`, `low_disk`). Exception text is never returned:
it can carry connection strings or paths. The detail goes to the log, once per
state change so a probe polling every few seconds cannot flood it.
"""
import asyncio
import logging
import os
import shutil
import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sqlalchemy import text

from app.core import metrics
from app.core.config import get_settings
from app.core.database import engine
from app.core.logging import log_event

logger = logging.getLogger(__name__)

CHECK_TIMEOUT_SECONDS = 3.0
_last_state: dict[str, bool] = {}


@dataclass
class CheckResult:
    name: str
    ok: bool
    reason: str | None = None

    def as_dict(self) -> dict:
        return {"status": "ok"} if self.ok else {"status": "fail", "reason": self.reason}


def _record(name: str, ok: bool, reason: str | None, exc: BaseException | None = None) -> CheckResult:
    metrics.set_gauge("his_ready", 1.0 if ok else 0.0, {"check": name})
    previous = _last_state.get(name)
    if previous is None or previous != ok:  # log transitions only
        _last_state[name] = ok
        if ok:
            if previous is False:  # a first healthy probe is just startup, not a recovery
                log_event(logger, logging.INFO, "readiness_recovered", check=name)
        else:
            log_event(
                logger,
                logging.ERROR,
                "readiness_failed",
                exc_info=exc,
                check=name,
                reason=reason,
                error_type=type(exc).__name__ if exc else None,
            )
    return CheckResult(name, ok, reason)


@lru_cache
def code_head_revision() -> str | None:
    """The Alembic head shipped with this build (None if migrations are absent)."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    backend_dir = Path(__file__).resolve().parents[2]
    ini = backend_dir / "alembic.ini"
    if not ini.exists():
        return None
    config = Config(str(ini))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    heads = ScriptDirectory.from_config(config).get_heads()
    return heads[0] if len(heads) == 1 else None


async def check_database() -> CheckResult:
    try:
        async with asyncio.timeout(CHECK_TIMEOUT_SECONDS):
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        return _record("database", False, "unreachable", exc)
    return _record("database", True, None)


async def check_migrations() -> CheckResult:
    head = code_head_revision()
    if head is None:
        return _record("migrations", False, "head_unknown")
    try:
        async with asyncio.timeout(CHECK_TIMEOUT_SECONDS):
            async with engine.connect() as conn:
                current = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar_one_or_none()
    except Exception as exc:  # noqa: BLE001
        return _record("migrations", False, "unreadable", exc)
    if current != head:
        return _record("migrations", False, "behind_head" if current else "not_migrated")
    return _record("migrations", True, None)


def _probe_storage() -> tuple[bool, str | None, BaseException | None]:
    settings = get_settings()
    root = Path(settings.file_storage_root)
    try:
        root.mkdir(parents=True, exist_ok=True)
        probe = root / f".readiness-{uuid.uuid4().hex}"
        with open(probe, "wb") as handle:  # a real write, flushed to the device
            handle.write(b"ok")
            handle.flush()
            os.fsync(handle.fileno())
        probe.unlink()
    except OSError as exc:
        return False, "not_writable", exc
    free_mb = shutil.disk_usage(root).free // (1024 * 1024)
    if free_mb < settings.storage_min_free_mb:
        return False, "low_disk", None
    return True, None, None


async def check_storage() -> CheckResult:
    try:
        ok, reason, exc = await asyncio.wait_for(asyncio.to_thread(_probe_storage), CHECK_TIMEOUT_SECONDS)
    except asyncio.TimeoutError as exc:
        return _record("storage", False, "timeout", exc)
    return _record("storage", ok, reason, exc)


async def run_readiness() -> list[CheckResult]:
    return list(await asyncio.gather(check_database(), check_migrations(), check_storage()))
