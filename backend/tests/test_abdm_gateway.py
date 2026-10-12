"""P8-B03: auth, timeout, retry, error mapping and logging of the ABDM
gateway HTTP layer (no network - httpx is driven by a mock transport)."""
import logging

import httpx
import pytest

from app.core.config import get_settings
from app.modules.abdm.adapter import (
    AbdmAuthError,
    AbdmRejectedError,
    AbdmTimeoutError,
    AbdmUnavailableError,
)
from app.modules.abdm.gateway_adapter import GatewayAbdmAdapter
from app.modules.abdm.mock_adapter import MockAbdmAdapter
from app.modules.abdm.service import _gateway_error


class _Adapter(GatewayAbdmAdapter):
    mode = "sandbox"


@pytest.fixture
def gateway(monkeypatch):
    """Returns `(adapter, calls, respond)`: `respond(handler)` installs the
    fake gateway; `calls` records every request path."""
    calls: list[str] = []
    sleeps: list[float] = []
    real_client = httpx.AsyncClient

    def respond(handler):
        def wrapped(request: httpx.Request) -> httpx.Response:
            calls.append(request.url.path)
            return handler(request)

        monkeypatch.setattr(
            httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(wrapped), **kw)
        )

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    adapter = _Adapter(
        base_url="https://gw.test/v0.5",
        client_id="the-client-id",
        client_secret="the-client-secret",
        max_retries=2,
        backoff_seconds=0.5,
        sleep=fake_sleep,
    )
    adapter.sleeps = sleeps
    return adapter, calls, respond


def _ok(request):
    return httpx.Response(200, json={"accessToken": "tok", "expiresIn": 600})


async def test_token_is_cached_between_calls(gateway):
    adapter, calls, respond = gateway
    respond(_ok)
    assert (await adapter.check_connection()).connected
    assert (await adapter.check_connection()).connected
    assert calls == ["/v0.5/sessions"]


async def test_transient_failure_is_retried_with_backoff_then_succeeds(gateway):
    adapter, calls, respond = gateway
    outcomes = iter([httpx.Response(503), httpx.Response(429), None])

    def handler(request):
        outcome = next(outcomes)
        return outcome or _ok(request)

    respond(handler)
    assert (await adapter.check_connection()).connected
    assert len(calls) == 3
    assert adapter.sleeps == [0.5, 1.0]


async def test_retries_are_bounded_and_map_to_unavailable(gateway):
    adapter, calls, respond = gateway
    respond(lambda r: httpx.Response(500))
    with pytest.raises(AbdmUnavailableError):
        await adapter._request("op", "GET", "/x")
    assert len(calls) == 3  # first attempt + 2 retries, each authenticating first


async def test_timeout_is_retried_then_mapped(gateway):
    adapter, calls, respond = gateway

    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    respond(handler)
    with pytest.raises(AbdmTimeoutError):
        await adapter._get_token()
    assert len(calls) == 3


async def test_auth_failure_is_not_retried(gateway):
    adapter, calls, respond = gateway
    respond(lambda r: httpx.Response(401))
    with pytest.raises(AbdmAuthError):
        await adapter._get_token()
    assert len(calls) == 1
    status = await adapter.check_connection()
    assert status.connected is False and "credentials" in status.message


async def test_client_error_is_not_retried(gateway):
    adapter, calls, respond = gateway

    def handler(request):
        return _ok(request) if request.url.path.endswith("/sessions") else httpx.Response(422)

    respond(handler)
    with pytest.raises(AbdmRejectedError):
        await adapter._request("op", "POST", "/care-contexts", json={})
    assert calls == ["/v0.5/sessions", "/v0.5/care-contexts"]


async def test_unauthorized_data_call_discards_the_cached_token(gateway):
    adapter, calls, respond = gateway
    respond(lambda r: _ok(r) if r.url.path.endswith("/sessions") else httpx.Response(401))
    with pytest.raises(AbdmAuthError):
        await adapter._request("op", "GET", "/x")
    assert adapter._token is None


async def test_logs_one_line_per_attempt_without_secrets(gateway, caplog):
    adapter, _, respond = gateway
    outcomes = iter([httpx.Response(503), None])
    respond(lambda r: next(outcomes) or _ok(r))
    with caplog.at_level(logging.INFO, logger="app.integrations.abdm"):
        await adapter.check_connection()
    lines = [r.getMessage() for r in caplog.records if r.name == "app.integrations.abdm"]
    assert len(lines) == 2
    assert "outcome=ABDM_UNAVAILABLE http_status=503" in lines[0] and "attempt=1/3" in lines[0]
    assert "outcome=success" in lines[1] and "http_status=200" in lines[1]
    joined = " ".join(lines)
    assert "the-client-secret" not in joined and "tok" not in joined.replace("operation", "")


@pytest.mark.parametrize(
    ("exc", "status"),
    [
        (AbdmTimeoutError(), 504),
        (AbdmUnavailableError(), 503),
        (AbdmAuthError(), 502),
        (AbdmRejectedError(), 400),
    ],
)
def test_adapter_errors_map_to_http_statuses(exc, status):
    mapped = _gateway_error(exc)
    assert mapped.status_code == status and mapped.code == exc.code


async def test_mock_simulation_modes(monkeypatch):
    settings = get_settings()
    adapter = MockAbdmAdapter()
    monkeypatch.setattr(settings, "abdm_mock_simulate", "timeout")
    with pytest.raises(AbdmTimeoutError):
        await adapter.request_otp(auth_method="MOBILE_OTP", identifier="9876543210")

    monkeypatch.setattr(settings, "abdm_mock_simulate", "flaky")
    flaky = MockAbdmAdapter()
    with pytest.raises(AbdmUnavailableError):
        await flaky.request_otp(auth_method="MOBILE_OTP", identifier="9876543210")
    assert (await flaky.request_otp(auth_method="MOBILE_OTP", identifier="9876543210")).transaction_id

    monkeypatch.setattr(settings, "abdm_mock_simulate", "")
    assert (await adapter.check_connection()).connected
