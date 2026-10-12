"""P8-B06 stage 3 (production readiness): the rollout gate itself."""
import pytest

from app.core.config import Settings
from app.modules.abdm.readiness import evaluate_readiness, is_ready

PRODUCTION = dict(
    environment="production",
    abdm_adapter="production",
    abdm_client_id="prod-client-id",
    abdm_client_secret="prod-client-secret",
    jwt_access_secret_key="a" * 40,
    jwt_refresh_secret_key="b" * 40,
    qr_signing_secret_key="c" * 40,
    public_base_url="https://his.example.com",
)


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **{**PRODUCTION, **overrides})


def _failed(settings: Settings, target: str = "production") -> set[str]:
    return {c.name for c in evaluate_readiness(settings, target) if not c.ok}


def test_fully_configured_production_is_ready():
    checks = evaluate_readiness(_settings(), "production", live_connected=True)
    assert is_ready(checks), [c for c in checks if not c.ok]


def test_mock_configuration_is_not_production_ready():
    local = Settings(_env_file=None)  # defaults: local + mock
    failed = _failed(local)
    assert {"adapter", "credentials", "non_local_environment", "public_callback_url"} <= failed


@pytest.mark.parametrize(
    ("override", "expected_failure"),
    [
        ({"abdm_adapter": "sandbox"}, "adapter"),
        ({"abdm_client_secret": ""}, "credentials"),
        ({"abdm_client_id": ""}, "credentials"),
        ({"abdm_base_url": "http://gateway.abdm.gov.in/v0.5"}, "https"),
        ({"abdm_base_url": "https://dev.abdm.gov.in/gateway/v0.5"}, "gateway_host"),
        ({"abdm_mock_simulate": "timeout"}, "no_failure_simulation"),
        ({"abdm_max_retries": 50}, "retry_policy"),
        ({"public_base_url": ""}, "public_callback_url"),
        ({"public_base_url": "http://his.example.com"}, "public_callback_url"),
    ],
)
def test_each_production_requirement_is_enforced(override, expected_failure):
    assert expected_failure in _failed(_settings(**override))


def test_unreachable_gateway_blocks_readiness():
    checks = evaluate_readiness(_settings(), "production", live_connected=False)
    assert not is_ready(checks)
    assert [c.name for c in checks if not c.ok] == ["live_connection"]


def test_sandbox_stage_does_not_require_production_hardening():
    sandbox = Settings(
        _env_file=None,
        abdm_adapter="sandbox",
        abdm_client_id="sbx-id",
        abdm_client_secret="sbx-secret",
    )  # local environment, dev signing keys, no public URL - fine for sandbox
    assert is_ready(evaluate_readiness(sandbox, "sandbox"))


def test_sandbox_stage_still_rejects_the_production_gateway():
    assert "gateway_host" in _failed(
        _settings(abdm_adapter="sandbox", abdm_base_url="https://gateway.abdm.gov.in/v0.5"), "sandbox"
    )


def test_unknown_stage_is_rejected():
    with pytest.raises(ValueError):
        evaluate_readiness(_settings(), "staging")


def test_readiness_output_never_contains_the_secret():
    text = " ".join(c.detail for c in evaluate_readiness(_settings(), "production", live_connected=True))
    assert "prod-client-secret" not in text and "a" * 40 not in text
