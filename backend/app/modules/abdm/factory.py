from __future__ import annotations

from app.modules.abdm.adapter import AbdmAdapter
from app.modules.abdm.mock_adapter import MockAbdmAdapter
from app.modules.abdm.production_adapter import ProductionAbdmAdapter
from app.modules.abdm.sandbox_adapter import SandboxAbdmAdapter

SANDBOX_URL = "https://dev.abdm.gov.in/gateway/v0.5"
PRODUCTION_URL = "https://gateway.abdm.gov.in/v0.5"

_mock_adapter = MockAbdmAdapter()  # shared so it keeps pending OTP transactions


def get_abdm_adapter() -> AbdmAdapter:
    """Selects the `AbdmAdapter` named by `Settings.abdm_adapter`."""
    from app.core.config import get_settings

    settings = get_settings()
    name = settings.abdm_adapter
    if name == "mock":
        return _mock_adapter
    if name == "sandbox":
        cls, default_url = SandboxAbdmAdapter, SANDBOX_URL
    elif name == "production":
        cls, default_url = ProductionAbdmAdapter, PRODUCTION_URL
    else:
        raise ValueError(f"Unknown ABDM adapter: {name!r}")
    return cls(
        base_url=settings.abdm_base_url or default_url,
        client_id=settings.abdm_client_id,
        client_secret=settings.abdm_client_secret.get_secret_value(),
        timeout_seconds=settings.abdm_timeout_seconds,
        max_retries=settings.abdm_max_retries,
        backoff_seconds=settings.abdm_retry_backoff_seconds,
    )
