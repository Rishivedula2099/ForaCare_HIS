from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core import readiness
from app.core.config import get_settings
from app.core.context import get_request_id
from app.core.database import check_database_connection
from app.core.exceptions import AppError
from app.core.responses import ApiResponse, error_response, success_response

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse, summary="Liveness check (is the process up?)")
async def health_check(request: Request):
    settings = get_settings()
    data = {"status": "ok", "app_name": settings.app_name, "version": settings.app_version}
    if settings.is_local:
        # The deployment's environment name is not for the public internet.
        data["environment"] = settings.environment
    return success_response(data, request_id=getattr(request.state, "request_id", None))


@router.get("/health/ready", response_model=ApiResponse, summary="Readiness check (database, migrations, storage)")
async def readiness_check(request: Request):
    """200 only when every check passes; otherwise 503 listing which failed and why
    (a reason code, never exception text). Use for load-balancer and monitor probes."""
    results = await readiness.run_readiness()
    checks = {r.name: r.as_dict() for r in results}
    if all(r.ok for r in results):
        return success_response({"status": "ready", "checks": checks}, request_id=getattr(request.state, "request_id", None))
    return JSONResponse(
        status_code=503,
        content=error_response(
            "NOT_READY",
            "One or more readiness checks failed.",
            request_id=get_request_id(),
        )
        | {"data": {"status": "not_ready", "checks": checks}},
    )


@router.get("/health/db", response_model=ApiResponse, summary="Readiness check (database connectivity only)")
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
