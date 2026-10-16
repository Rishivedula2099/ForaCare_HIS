"""P10-F02: platform-operator endpoints. Everything here requires an
authenticated SUPER_ADMIN holding `tenants.manage`; there is no anonymous or
tenant-admin path to creating a hospital."""
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.permissions import require_platform_operator
from app.core.rate_limit import rate_limit
from app.core.responses import ApiResponse, success_response
from app.modules.auth.models import User
from app.modules.platform import service
from app.modules.platform.schemas import TenantSetupRequest

router = APIRouter(prefix="/platform", tags=["platform"])

_settings = get_settings()
_limit_setup = rate_limit("platform-setup", limit=_settings.rate_limit_sensitive_per_minute)
_limit_lookup = rate_limit("platform-lookup", limit=_settings.rate_limit_sensitive_per_minute * 6)


def _rid(request: Request):
    return getattr(request.state, "request_id", None)


@router.get("/setup-options", response_model=ApiResponse, summary="Allowed values for the setup wizard")
async def setup_options(request: Request, _: User = Depends(require_platform_operator)):
    return success_response(service.setup_options().model_dump(mode="json"), request_id=_rid(request))


@router.get(
    "/setup/availability",
    response_model=ApiResponse,
    summary="Are these setup codes/usernames still free?",
    dependencies=[Depends(_limit_lookup)],
)
async def availability(
    request: Request,
    organization_code: str | None = Query(default=None, max_length=50),
    facility_code: str | None = Query(default=None, max_length=50),
    username: str | None = Query(default=None, max_length=100),
    email: str | None = Query(default=None, max_length=255),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_platform_operator),
):
    result = await service.check_availability(
        db, organization_code=organization_code, facility_code=facility_code, username=username, email=email
    )
    return success_response(result.model_dump(mode="json"), request_id=_rid(request))


@router.post(
    "/tenants",
    response_model=ApiResponse,
    status_code=201,
    summary="Create a hospital (tenant), its first facility and its first administrator",
    dependencies=[Depends(_limit_setup)],
)
async def create_tenant(
    payload: TenantSetupRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    operator: User = Depends(require_platform_operator),
):
    result = await service.create_tenant_with_facility(db, payload, operator)
    return success_response(result.model_dump(mode="json"), request_id=_rid(request))
