"""Shared HTTP layer for the sandbox and production ABDM adapters (P8-B03).

Both talk to the same gateway API (v0.5) and differ only in base URL and
credentials, so everything about *how* we call the gateway lives here once:

* authentication - a cached bearer token from `POST /sessions`, refreshed
  shortly before it expires and discarded on a 401;
* timeouts - one per-request timeout;
* retry - transient failures (timeouts, connection errors, 429, 5xx) are
  retried with exponential backoff; auth and 4xx errors never are;
* error mapping - every failure becomes a typed `AbdmError` subclass, so
  callers never see httpx exceptions or raw gateway bodies;
* integration logging - one structured log line per attempt (operation,
  attempt, outcome, status, duration). Credentials, tokens and request or
  response bodies (which carry Aadhaar/ABHA identifiers) are never logged.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from app.modules.abdm.adapter import (
    AbdmAdapter,
    AbdmAuthError,
    AbdmConnectionStatus,
    AbdmError,
    AbdmNotConfiguredError,
    AbdmNotImplementedError,
    AbdmOtpChallenge,
    AbdmRejectedError,
    AbdmTimeoutError,
    AbdmUnavailableError,
    AbhaProfile,
)

logger = logging.getLogger("app.integrations.abdm")

_TOKEN_REFRESH_MARGIN_SECONDS = 30
_DEFAULT_TOKEN_TTL_SECONDS = 600


class GatewayAbdmAdapter(AbdmAdapter):
    def __init__(
        self,
        *,
        base_url: str,
        client_id: str,
        client_secret: str,
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        backoff_seconds: float = 0.5,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._backoff = backoff_seconds
        self._sleep = sleep
        self._token: str | None = None
        self._token_expires_at = 0.0

    def _require_configured(self) -> None:
        if not (self._base_url and self._client_id and self._client_secret):
            # Which setting is missing is operator information: logged, never
            # returned to API callers (who see only the generic message).
            logger.error("ABDM %s adapter is missing ABDM_BASE_URL/CLIENT_ID/CLIENT_SECRET", self.mode)
            raise AbdmNotConfiguredError("The ABDM integration is not configured.")

    # -- transport ---------------------------------------------------------

    async def _send_once(
        self, method: str, path: str, *, json: Any, token: str | None
    ) -> httpx.Response:
        """One HTTP attempt; maps transport failures and error statuses."""
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.request(
                    method, f"{self._base_url}{path}", json=json, headers=headers
                )
        except httpx.TimeoutException as exc:
            raise AbdmTimeoutError() from exc
        except httpx.HTTPError as exc:
            raise AbdmUnavailableError() from exc

        status = response.status_code
        if status < 400:
            return response
        if status in (401, 403):
            error: AbdmError = AbdmAuthError()
        elif status == 429 or status >= 500:
            error = AbdmUnavailableError()
        else:
            error = AbdmRejectedError()
        error.http_status = status
        raise error

    async def _request(
        self,
        operation: str,
        method: str,
        path: str,
        *,
        json: Any = None,
        authenticated: bool = True,
    ) -> httpx.Response:
        """Calls the gateway with auth, retry, error mapping and logging."""
        self._require_configured()
        # Authenticating has its own retry (it is a `_request` itself), so
        # it happens once up front rather than inside this call's retry loop.
        token = await self._get_token() if authenticated else None
        attempts = self._max_retries + 1
        for attempt in range(1, attempts + 1):
            started = time.monotonic()
            error: AbdmError | None = None
            response: httpx.Response | None = None
            try:
                response = await self._send_once(method, path, json=json, token=token)
            except AbdmAuthError as exc:
                if authenticated:
                    self._token = None  # stale or revoked - re-authenticate next time
                error = exc
            except AbdmError as exc:
                error = exc

            logger.info(
                "abdm_call mode=%s operation=%s attempt=%d/%d outcome=%s http_status=%s duration_ms=%d",
                self.mode,
                operation,
                attempt,
                attempts,
                "success" if error is None else error.code,
                response.status_code if response is not None else getattr(error, "http_status", "-"),
                round((time.monotonic() - started) * 1000),
            )
            if error is None:
                assert response is not None
                return response
            if not isinstance(error, (AbdmTimeoutError, AbdmUnavailableError)) or attempt == attempts:
                raise error
            await self._sleep(self._backoff * 2 ** (attempt - 1))
        raise AssertionError("unreachable")  # pragma: no cover

    # -- authentication ----------------------------------------------------

    async def _get_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token
        response = await self._request(
            "create_session",
            "POST",
            "/sessions",
            json={"clientId": self._client_id, "clientSecret": self._client_secret},
            authenticated=False,
        )
        try:
            body = response.json()
            token = body["accessToken"]
        except (ValueError, KeyError, TypeError) as exc:
            raise AbdmUnavailableError("ABDM returned an unreadable session response.") from exc
        ttl = body.get("expiresIn") if isinstance(body.get("expiresIn"), (int, float)) else None
        ttl = ttl or _DEFAULT_TOKEN_TTL_SECONDS
        self._token = token
        self._token_expires_at = time.monotonic() + max(ttl - _TOKEN_REFRESH_MARGIN_SECONDS, 0)
        return token

    # -- AbdmAdapter -------------------------------------------------------

    async def check_connection(self) -> AbdmConnectionStatus:
        try:
            await self._get_token()
        except AbdmError as exc:
            return AbdmConnectionStatus(mode=self.mode, connected=False, message=exc.message)
        return AbdmConnectionStatus(mode=self.mode, connected=True)

    async def request_otp(self, *, auth_method: str, identifier: str) -> AbdmOtpChallenge:
        raise AbdmNotImplementedError(
            f"ABDM {self.mode} OTP request is pending NHA credential enrollment."
        )

    async def verify_otp(self, *, transaction_id: str, otp: str) -> AbhaProfile:
        raise AbdmNotImplementedError(
            f"ABDM {self.mode} OTP verification is pending NHA credential enrollment."
        )
