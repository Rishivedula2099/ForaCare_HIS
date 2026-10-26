import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core import metrics
from app.core.context import init_request_state, set_request_id
from app.core.logging import log_event

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
# A client-supplied ID is echoed into logs and a response header, so accept
# only a short, inert charset (blocks log injection / header smuggling).
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

# Probe endpoints are polled every few seconds; logging each success at INFO
# would bury real traffic, so successes go to DEBUG (failures still log).
_QUIET_PREFIXES = ("/api/v1/health", "/internal/")


def route_template(request: Request) -> str:
    """The matched route as a TEMPLATE (e.g. /api/v1/patients/{patient_id}), built from
    the real URL by replacing each matched path parameter with its name. Never the
    concrete URL: that carries identifiers and would make metric labels unbounded.

    Built from the URL rather than read from `route.path` because FastAPI versions
    differ in whether a nested router's `route.path` carries its mount prefix (the
    pinned production version dropped `/api/v1`)."""
    if request.scope.get("route") is None:
        return "unmatched"
    remaining = {name: str(value) for name, value in (request.scope.get("path_params") or {}).items()}
    segments = []
    for segment in request.url.path.split("/"):
        for name, value in list(remaining.items()):
            if segment == value:
                segment = "{" + name + "}"
                del remaining[name]
                break
        segments.append(segment)
    return "/".join(segments)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Assigns a request/correlation ID to every request, echoes it back, and
    writes one structured access-log line plus request metrics when it ends."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        supplied = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = supplied if _SAFE_REQUEST_ID.match(supplied) else str(uuid.uuid4())
        set_request_id(request_id)
        request.state.request_id = request_id
        state = init_request_state()

        start_time = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
        finally:
            # Runs for responses AND for exceptions that escape to the error handler.
            self._record(request, state, status, time.perf_counter() - start_time)

        response.headers[REQUEST_ID_HEADER] = request_id
        return response

    @staticmethod
    def _record(request: Request, state: dict, status: int, seconds: float) -> None:
        route = route_template(request)
        method = request.method
        metrics.inc(
            "his_http_requests_total", {"method": method, "route": route, "status": metrics.status_class(status)}
        )
        metrics.observe("his_http_request_duration_seconds", seconds, {"route": route})

        quiet = status < 400 and request.url.path.startswith(_QUIET_PREFIXES)
        level = logging.DEBUG if quiet else logging.WARNING if status >= 500 else logging.INFO
        # Path only: the query string can carry patient searches and QR signatures.
        log_event(
            logger,
            level,
            "http_request",
            http_method=method,
            path=request.url.path[:200] if route == "unmatched" else route,
            status=status,
            duration_ms=round(seconds * 1000, 2),
            client_ip=request.client.host if request.client else None,
            **state,
        )
