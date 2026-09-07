from fastapi import APIRouter, Request

from app.core.config import get_settings
from app.core.database import check_database_connection
from app.core.exceptions import AppError
from app.core.responses import ApiResponse, success_response

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse, summary="Liveness check")
async def health_check(request: Request):
    settings = get_settings()
    return success_response(
        {
            "status": "ok",
            "app_name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        },
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/health/db", response_model=ApiResponse, summary="Readiness check (database connectivity)")
async def health_check_db(request: Request):
    if not await check_database_connection():
        raise AppError(
            "Database is not reachable.",
            code="DATABASE_UNAVAILABLE",
            status_code=503,
        )

    return success_response(
        {"status": "ok", "database": "reachable"},
        request_id=getattr(request.state, "request_id", None),
    )
