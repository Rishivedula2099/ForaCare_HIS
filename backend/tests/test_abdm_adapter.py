"""P8-B01: ABDM adapter selection and behavior (no database or network)."""
import httpx
import pytest

from app.core.config import get_settings
from app.modules.abdm.adapter import AbdmError, AbdmNotImplementedError
from app.modules.abdm.factory import get_abdm_adapter
from app.modules.abdm.mock_adapter import MockAbdmAdapter
from app.modules.abdm.production_adapter import ProductionAbdmAdapter
from app.modules.abdm.sandbox_adapter import SandboxAbdmAdapter


@pytest.fixture
def abdm_settings(monkeypatch):
    settings = get_settings()

    def _set(**values):
        for key, value in values.items():
            monkeypatch.setattr(settings, key, value)

    return _set


def test_factory_selects_adapter_by_setting(abdm_settings):
    abdm_settings(abdm_adapter="mock")
    assert isinstance(get_abdm_adapter(), MockAbdmAdapter)
    abdm_settings(abdm_adapter="sandbox")
    assert isinstance(get_abdm_adapter(), SandboxAbdmAdapter)
    abdm_settings(abdm_adapter="production")
    assert isinstance(get_abdm_adapter(), ProductionAbdmAdapter)
    abdm_settings(abdm_adapter="bogus")
    with pytest.raises(ValueError):
        get_abdm_adapter()


async def test_mock_otp_flow_returns_deterministic_profile():
    adapter = MockAbdmAdapter()
    status = await adapter.check_connection()
    assert status.mode == "mock" and status.connected

    first = await adapter.request_otp(auth_method="MOBILE_OTP", identifier="9876543210")
    profile = await adapter.verify_otp(transaction_id=first.transaction_id, otp="123456")
    assert len(profile.abha_number.replace("-", "")) == 14

    second = await adapter.request_otp(auth_method="MOBILE_OTP", identifier="9876543210")
    again = await adapter.verify_otp(transaction_id=second.transaction_id, otp="654321")
    assert again.abha_number == profile.abha_number


async def test_mock_rejects_unknown_transaction_and_bad_otp():
    adapter = MockAbdmAdapter()
    with pytest.raises(AbdmError):
        await adapter.verify_otp(transaction_id="nope", otp="123456")
    challenge = await adapter.request_otp(auth_method="MOBILE_OTP", identifier="9876543210")
    with pytest.raises(AbdmError):
        await adapter.verify_otp(transaction_id=challenge.transaction_id, otp="12")


async def test_gateway_adapter_without_credentials_reports_disconnected():
    adapter = SandboxAbdmAdapter(base_url="https://x.invalid", client_id="", client_secret="")
    status = await adapter.check_connection()
    assert status.mode == "sandbox"
    assert status.connected is False
    assert status.message == "The ABDM integration is not configured."  # no env var names leak


async def test_gateway_adapter_connection_follows_session_response(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/gateway/v0.5/sessions"
        return httpx.Response(200, json={"accessToken": "tok"})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    adapter = ProductionAbdmAdapter(
        base_url="https://gateway.abdm.gov.in/gateway/v0.5", client_id="id", client_secret="s"
    )
    assert (await adapter.check_connection()).connected is True

    def failing(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={})

    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(failing), **kw),
    )
    fresh = ProductionAbdmAdapter(
        base_url="https://gateway.abdm.gov.in/gateway/v0.5", client_id="id", client_secret="s"
    )
    assert (await fresh.check_connection()).connected is False


async def test_gateway_otp_operations_not_yet_implemented():
    adapter = SandboxAbdmAdapter(base_url="https://x.invalid", client_id="a", client_secret="b")
    with pytest.raises(AbdmNotImplementedError):
        await adapter.request_otp(auth_method="MOBILE_OTP", identifier="9876543210")
