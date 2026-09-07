import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.context import get_request_id
from app.core.responses import ErrorDetail, error_response

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for domain/application errors that map to a known HTTP status."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "APP_ERROR"

    def __init__(self, message: str, *, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
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


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request_id = get_request_id()
        logger.warning("Application error: %s", exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(exc.code, exc.message, request_id=request_id),
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
        request_id = get_request_id()
        logger.exception("Unhandled exception while processing request")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                "INTERNAL_SERVER_ERROR",
                "An unexpected error occurred.",
                request_id=request_id,
            ),
        )
