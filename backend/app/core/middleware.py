import logging
import re
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.context import set_request_id

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
# A client-supplied ID is echoed into logs and a response header, so accept
# only a short, inert charset (blocks log injection / header smuggling).
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Assigns a request/correlation ID to every request and echoes it back."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        supplied = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = supplied if _SAFE_REQUEST_ID.match(supplied) else str(uuid.uuid4())
        set_request_id(request_id)
        request.state.request_id = request_id

        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000

        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "%s %s -> %s (%.2fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response
