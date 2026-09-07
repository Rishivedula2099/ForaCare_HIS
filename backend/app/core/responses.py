from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseMeta(BaseModel):
    request_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ErrorModel(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class ApiResponse(BaseModel, Generic[T]):
    """Standard success envelope for all /api/v1 responses."""

    success: bool = True
    data: T | None = None
    error: None = None
    meta: ResponseMeta


class ApiErrorResponse(BaseModel):
    """Standard error envelope for all /api/v1 responses."""

    success: bool = False
    data: None = None
    error: ErrorModel
    meta: ResponseMeta


def success_response(data: Any, request_id: str | None = None) -> dict:
    return ApiResponse(data=data, meta=ResponseMeta(request_id=request_id)).model_dump(mode="json")


def error_response(
    code: str,
    message: str,
    request_id: str | None = None,
    details: list[ErrorDetail] | None = None,
) -> dict:
    return ApiErrorResponse(
        error=ErrorModel(code=code, message=message, details=details or []),
        meta=ResponseMeta(request_id=request_id),
    ).model_dump(mode="json")
