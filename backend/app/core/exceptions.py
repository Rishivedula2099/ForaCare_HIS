import hashlib
import logging
import traceback

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core import alerting, metrics
from app.core.context import get_request_id, set_request_id
from app.core.logging import log_event
from app.core.responses import ErrorDetail, error_response

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for domain/application errors that map to a known HTTP status."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "APP_ERROR"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: list[tuple[str, str]] | None = None,
    ):
        super().__init__(message)
        self.message = message
        # (field, message) pairs, so a form can show each problem next to its input.
        self.details = details or []
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "NOT_FOUND"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"


class UnauthorizedError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    code = "FORBIDDEN"


def _http_status_to_code(status_code: int) -> str:
    return {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
    }.get(status_code, "HTTP_ERROR")


def error_fingerprint(exc: BaseException) -> str:
    """Stable id for "the same bug": exception type + the innermost frame inside
    our own code. Lets alerts and dashboards group repeats without parsing text."""
    frames = traceback.extract_tb(exc.__traceback__)
    ours = [f for f in frames if "/app/" in f.filename.replace("\\", "/") and "site-packages" not in f.filename]
    frame = (ours or frames or [None])[-1]
    where = f"{frame.filename.replace(chr(92), '/').split('/app/')[-1]}:{frame.name}" if frame else "unknown"
    return hashlib.sha1(f"{type(exc).__name__}|{where}".encode()).hexdigest()[:12]


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request_id = get_request_id()
        server_side = exc.status_code >= 500
        if server_side:
            metrics.inc("his_server_errors_total", {"code": exc.code})
        logger.log(
            logging.ERROR if server_side else logging.WARNING,
            "Application error: %s",
            exc.message,
            extra={"event": "app_error", "fields": {"code": exc.code, "status": exc.status_code}},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                exc.code,
                exc.message,
                request_id=request_id,
                details=[ErrorDetail(field=f, message=m) for f, m in exc.details],
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        request_id = get_request_id()
        detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(_http_status_to_code(exc.status_code), detail, request_id=request_id),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = get_request_id()
        details = [
            ErrorDetail(field=".".join(str(loc) for loc in err["loc"]), message=err["msg"])
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error_response(
                "VALIDATION_ERROR",
                "Request validation failed.",
                request_id=request_id,
                details=details,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # This handler runs in the outermost error middleware, outside the task in which
        # the correlation middleware set the ContextVar - but `request.state` is shared via
        # the ASGI scope. Without this the 500 response and its log line had no request id.
        request_id = getattr(request.state, "request_id", None) or get_request_id()
        if request_id:
            set_request_id(request_id)
        fingerprint = error_fingerprint(exc)
        from app.core.middleware import route_template

        route = route_template(request)
        metrics.inc("his_unhandled_exceptions_total")
        log_event(
            logger,
            logging.ERROR,
            "unhandled_exception",
            exc_info=exc,  # traceback is scrubbed (SQL values, tokens, passwords) by the log filter
            error_type=type(exc).__name__,
            error_fingerprint=fingerprint,
            http_method=request.method,
            route=route,
        )
        alerting.notify(
            f"error:{fingerprint}",
            f"Unhandled {type(exc).__name__} in {request.method} {route}",
            fingerprint=fingerprint,
        )
        # The reference lets a user report the failure and an operator find the exact
        # log line; the cause itself never reaches the client.
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                "INTERNAL_SERVER_ERROR",
                f"An unexpected error occurred. If it continues, give support this reference: {request_id}.",
                request_id=request_id,
            ),
            headers={"X-Request-ID": request_id} if request_id else None,
        )
