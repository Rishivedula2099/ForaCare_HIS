"""P10-S01: pure-ASGI request-hardening middleware for the production topology
(browser -> TLS-terminating reverse proxy -> this API).

All four are ASGI middleware rather than `BaseHTTPMiddleware` so they also see
WebSocket handshakes and never buffer bodies.
"""
import ipaddress
import json
import logging
from urllib.parse import urlparse

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.context import get_request_id
from app.core.responses import error_response

logger = logging.getLogger(__name__)

# Container health checks hit the API directly over plain HTTP.
HTTPS_EXEMPT_PATHS = ("/api/v1/health",)
_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


async def _reject(send: Send, status: int, code: str, message: str) -> None:
    body = json.dumps(error_response(code, message, request_id=get_request_id())).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
        }
    )
    await send({"type": "http.response.body", "body": body})


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key == name:
            return value.decode("latin1")
    return None


class TrustedProxyMiddleware:
    """Takes the client address and scheme from X-Forwarded-For/-Proto, but
    only when the TCP peer is one of `networks` (so a client talking to the API
    directly cannot forge its IP or claim HTTPS). Walks X-Forwarded-For from
    the right, skipping trusted proxies, so values a client prepends are
    ignored."""

    def __init__(self, app: ASGIApp, networks: list) -> None:
        self.app = app
        self.networks = networks

    def _trusted(self, host: str | None) -> bool:
        try:
            address = ipaddress.ip_address(host or "")
        except ValueError:
            return False
        return any(address in network for network in self.networks)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket") and self.networks:
            client = scope.get("client")
            if client and self._trusted(client[0]):
                forwarded_for = _header(scope, b"x-forwarded-for")
                if forwarded_for:
                    hops = [hop.strip() for hop in forwarded_for.split(",") if hop.strip()]
                    for hop in reversed(hops):
                        if not self._trusted(hop):
                            scope["client"] = (hop, 0)
                            break
                proto = (_header(scope, b"x-forwarded-proto") or "").split(",")[0].strip().lower()
                if proto in ("http", "https"):
                    scope["scheme"] = proto if scope["type"] == "http" else proto.replace("http", "ws")
        await self.app(scope, receive, send)


class HttpsOnlyMiddleware:
    """Refuses anything that did not arrive over HTTPS (as reported by the
    trusted proxy). Defence in depth behind the proxy's own http->https
    redirect: even a misrouted plain-HTTP request never reaches a handler."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket") and scope.get("scheme") not in ("https", "wss"):
            path = scope.get("path", "")
            if not path.startswith(HTTPS_EXEMPT_PATHS):
                logger.warning("security.insecure_transport_rejected path=%s", path)
                if scope["type"] == "websocket":
                    await send({"type": "websocket.close", "code": 4403})
                else:
                    await _reject(send, 400, "HTTPS_REQUIRED", "This API is only available over HTTPS.")
                return
        await self.app(scope, receive, send)


class RequestSizeLimitMiddleware:
    """413 for any body over `max_bytes` - by Content-Length up front, and by
    counting streamed/chunked bodies that declare no length."""

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        declared = _header(scope, b"content-length")
        if declared and declared.isdigit() and int(declared) > self.max_bytes:
            await _reject(send, 413, "PAYLOAD_TOO_LARGE", "The request body is too large.")
            return

        received = 0
        responded = False

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise _BodyTooLarge()
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal responded
            if message["type"] == "http.response.start":
                responded = True
            await send(message)

        try:
            await self.app(scope, limited_receive, tracking_send)
        except _BodyTooLarge:
            if not responded:
                await _reject(send, 413, "PAYLOAD_TOO_LARGE", "The request body is too large.")


class _BodyTooLarge(Exception):
    pass


class SameOriginWritesMiddleware:
    """CSRF defence in depth on top of SameSite cookies: a state-changing
    request that carries an Origin header must come from this site (the Host it
    was sent to) or from an explicitly trusted origin. Requests without an
    Origin (non-browser clients) are not browser-driven CSRF and pass."""

    def __init__(self, app: ASGIApp, trusted_origins: list[str]) -> None:
        self.app = app
        self.trusted = {o.rstrip("/").lower() for o in trusted_origins}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] in _UNSAFE_METHODS:
            origin = _header(scope, b"origin")
            if origin is not None and not self._allowed(scope, origin):
                logger.warning("security.cross_origin_write_rejected origin=%s path=%s", origin[:100], scope.get("path"))
                await _reject(send, 403, "FORBIDDEN", "Cross-origin request rejected.")
                return
        await self.app(scope, receive, send)

    def _allowed(self, scope: Scope, origin: str) -> bool:
        normalized = origin.rstrip("/").lower()
        if normalized in self.trusted:
            return True
        parsed = urlparse(normalized)
        host = (_header(scope, b"host") or "").lower()
        return bool(parsed.netloc) and parsed.netloc == host and parsed.scheme == scope.get("scheme", "http")
