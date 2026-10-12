"""P8-B06 stage 1 (mock): one behavioral contract, run against every adapter
so the mock cannot drift from what the sandbox/production adapters promise.
The gateway adapters are driven by an in-process fake gateway (no network)."""
import httpx
import pytest

from app.modules.abdm.adapter import AbdmAdapter, AbdmConnectionStatus, AbdmError
from app.modules.abdm.mock_adapter import MockAbdmAdapter
from app.modules.abdm.production_adapter import ProductionAbdmAdapter
from app.modules.abdm.sandbox_adapter import SandboxAbdmAdapter

SECRET = "contract-test-secret-value"


@pytest.fixture
def fake_gateway(monkeypatch):
    """Installs a gateway that answers /sessions; `state["up"]` toggles it."""
    state = {"up": True}
    real_client = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        if not state["up"]:
            return httpx.Response(503)
        return httpx.Response(200, json={"accessToken": "tok", "expiresIn": 600})

    monkeypatch.setattr(
        httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)
    )
    return state


async def _no_sleep(_: float) -> None:
    return None


def _build(kind: str) -> AbdmAdapter:
    if kind == "mock":
        return MockAbdmAdapter()
    cls = SandboxAbdmAdapter if kind == "sandbox" else ProductionAbdmAdapter
    return cls(
        base_url="https://gw.test/v0.5", client_id="cid", client_secret=SECRET, sleep=_no_sleep
    )


@pytest.fixture(params=["mock", "sandbox", "production"])
def adapter(request, fake_gateway) -> AbdmAdapter:
    return _build(request.param)


async def test_connection_status_reports_its_own_mode(adapter):
    status = await adapter.check_connection()
    assert isinstance(status, AbdmConnectionStatus)
    assert status.mode == adapter.mode
    assert status.connected is True


async def test_status_message_never_contains_the_secret(adapter):
    status = await adapter.check_connection()
    assert SECRET not in (status.message or "")


@pytest.mark.parametrize("kind", ["sandbox", "production"])
async def test_unreachable_gateway_is_reported_not_raised(kind, fake_gateway):
    fake_gateway["up"] = False
    status = await _build(kind).check_connection()
    assert status.connected is False and status.message
    assert SECRET not in status.message


async def test_otp_operations_only_ever_raise_abdm_errors(adapter):
    """Whatever the stage, callers handle one exception family - a failure is
    never a raw httpx/KeyError leaking out of an adapter."""
    try:
        challenge = await adapter.request_otp(auth_method="MOBILE_OTP", identifier="9876543210")
        profile = await adapter.verify_otp(transaction_id=challenge.transaction_id, otp="123456")
    except AbdmError:
        return  # gateway adapters: OTP flow pending NHA credentials
    assert len(profile.abha_number.replace("-", "")) == 14 and "@" in profile.abha_address


async def test_wrong_transaction_is_never_verified(adapter):
    with pytest.raises(AbdmError):
        await adapter.verify_otp(transaction_id="does-not-exist", otp="123456")
