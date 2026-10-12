"""ABDM rollout readiness (P8-B06).

The integration is rolled out in three stages - mock (offline development),
sandbox (NHA test gateway) and production - and each stage has requirements
that must hold before moving on. `evaluate_readiness` checks a configuration
against a target stage and reports every unmet requirement, so "are we ready
for production?" is a command (`python scripts/abdm_readiness.py`), not a
judgment call. It inspects configuration only; pass a live connection result
in for the connectivity check.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from app.core.config import Settings
from app.modules.abdm.factory import PRODUCTION_URL, SANDBOX_URL

STAGES = ("sandbox", "production")


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    ok: bool
    detail: str


def _host(url: str) -> str:
    return urlparse(url).hostname or ""


def evaluate_readiness(
    settings: Settings, target: str, *, live_connected: bool | None = None
) -> list[ReadinessCheck]:
    """Returns one check per requirement for `target` ("sandbox" or
    "production"). `live_connected` is the result of a real
    `check_connection()`, or None when it wasn't attempted."""
    if target not in STAGES:
        raise ValueError(f"Unknown target stage: {target!r}")

    checks: list[ReadinessCheck] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append(ReadinessCheck(name, ok, detail))

    check(
        "adapter",
        settings.abdm_adapter == target,
        f"ABDM_ADAPTER is {settings.abdm_adapter!r}, expected {target!r}",
    )
    check(
        "credentials",
        bool(settings.abdm_client_id and settings.abdm_client_secret.get_secret_value()),
        "ABDM_CLIENT_ID and ABDM_CLIENT_SECRET are set"
        if settings.abdm_client_id and settings.abdm_client_secret.get_secret_value()
        else "ABDM_CLIENT_ID and/or ABDM_CLIENT_SECRET are missing",
    )

    base_url = settings.abdm_base_url or (PRODUCTION_URL if target == "production" else SANDBOX_URL)
    expected_host = _host(PRODUCTION_URL if target == "production" else SANDBOX_URL)
    check("https", base_url.startswith("https://"), f"gateway URL is {base_url}")
    check(
        "gateway_host",
        _host(base_url) == expected_host,
        f"gateway host is {_host(base_url)!r}, the {target} gateway is {expected_host!r}",
    )
    check(
        "no_failure_simulation",
        not settings.abdm_mock_simulate,
        "ABDM_MOCK_SIMULATE is empty" if not settings.abdm_mock_simulate else "ABDM_MOCK_SIMULATE is set",
    )
    check(
        "retry_policy",
        0 < settings.abdm_timeout_seconds <= 30 and 0 <= settings.abdm_max_retries <= 5,
        f"timeout={settings.abdm_timeout_seconds}s, max_retries={settings.abdm_max_retries}",
    )

    if target == "production":
        check(
            "non_local_environment",
            not settings.is_local,
            f"ENVIRONMENT is {settings.environment!r}",
        )
        insecure = [
            name.upper()
            for name in ("jwt_access_secret_key", "jwt_refresh_secret_key", "qr_signing_secret_key")
            if "local-dev-only" in getattr(settings, name)
        ]
        check(
            "app_secrets",
            not insecure,
            "signing keys are overridden" if not insecure else f"public dev defaults in use: {', '.join(insecure)}",
        )
        check(
            "public_callback_url",
            settings.public_base_url.startswith("https://"),
            "PUBLIC_BASE_URL is https (ABDM callbacks need a public HTTPS endpoint)"
            if settings.public_base_url.startswith("https://")
            else "PUBLIC_BASE_URL must be the public https origin for ABDM callbacks",
        )
        check("secure_cookies", settings.cookie_secure, f"cookie_secure={settings.cookie_secure}")

    if live_connected is not None:
        check(
            "live_connection",
            live_connected,
            "gateway session was created" if live_connected else "could not create a gateway session",
        )
    return checks


def is_ready(checks: list[ReadinessCheck]) -> bool:
    return all(c.ok for c in checks)
