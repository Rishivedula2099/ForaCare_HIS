"""P10-B02: platform-operator management of existing organisations (tenants).
Every route requires an authenticated SUPER_ADMIN holding `tenants.manage`."""
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.permissions import require_platform_operator
from app.core.rate_limit import rate_limit
from app.core.responses import ApiResponse, success_response
from app.modules.auth.models import User
from app.modules.facilities.schemas import StatusChangeRequest
from app.modules.platform import lifecycle_service as service
from app.modules.platform.lifecycle_schemas import (
    AssignAdministratorRequest,
    FacilityCreateInTenantRequest,
    TenantUpdateRequest,
)

router = APIRouter(prefix="/platform", tags=["platform"])
_limit = rate_limit("platform-lifecycle", limit=get_settings().rate_limit_sensitive_per_minute)


def _rid(request: Request):
    return getattr(request.state, "request_id", None)


@router.get("/organisations", response_model=ApiResponse, summary="List every organisation with status and size")
async def list_tenants(
    request: Request, db: AsyncSession = Depends(get_db), _: User = Depends(require_platform_operator)
):
    tenants = await service.list_tenants(db)
    return success_response([t.model_dump(mode="json") for t in tenants], request_id=_rid(request))


@router.get("/organisations/{tenant_id}", response_model=ApiResponse, summary="One organisation: facilities and administrators")
async def get_tenant(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_platform_operator),
):
    return success_response((await service.get_tenant_detail(db, tenant_id)).model_dump(mode="json"), request_id=_rid(request))


@router.patch("/organisations/{tenant_id}", response_model=ApiResponse, summary="Rename an organisation")
async def update_tenant(
    tenant_id: uuid.UUID,
    payload: TenantUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    operator: User = Depends(require_platform_operator),
):
    result = await service.update_tenant(db, tenant_id, payload, operator)
    return success_response(result.model_dump(mode="json"), request_id=_rid(request))


@router.post(
    "/organisations/{tenant_id}/suspend",
    response_model=ApiResponse,
    summary="Suspend an organisation: ends all its sessions; reversible",
    dependencies=[Depends(_limit)],
)
async def suspend_tenant(
    tenant_id: uuid.UUID,
    payload: StatusChangeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    operator: User = Depends(require_platform_operator),
):
    result = await service.suspend_tenant(db, tenant_id, payload.reason, operator)
    return success_response(result.model_dump(mode="json"), request_id=_rid(request))


@router.post(
    "/organisations/{tenant_id}/reactivate",
    response_model=ApiResponse,
    summary="Reactivate a suspended organisation",
    dependencies=[Depends(_limit)],
)
async def reactivate_tenant(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    operator: User = Depends(require_platform_operator),
):
    result = await service.reactivate_tenant(db, tenant_id, operator)
    return success_response(result.model_dump(mode="json"), request_id=_rid(request))


@router.post(
    "/organisations/{tenant_id}/facilities",
    response_model=ApiResponse,
    status_code=201,
    summary="Add a facility to an organisation",
    dependencies=[Depends(_limit)],
)
async def create_facility(
    tenant_id: uuid.UUID,
    payload: FacilityCreateInTenantRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    operator: User = Depends(require_platform_operator),
):
    facility = await service.create_facility_in_tenant(db, tenant_id, payload.facility, operator)
    return success_response(facility.model_dump(mode="json"), request_id=_rid(request))


@router.post(
    "/organisations/{tenant_id}/facilities/{facility_id}/deactivate",
    response_model=ApiResponse,
    summary="Deactivate a facility (same safeguards a Hospital Admin faces)",
    dependencies=[Depends(_limit)],
)
async def deactivate_facility(
    tenant_id: uuid.UUID,
    facility_id: uuid.UUID,
    payload: StatusChangeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    operator: User = Depends(require_platform_operator),
):
    facility = await service.set_facility_status(db, tenant_id, facility_id, operator, active=False, reason=payload.reason)
    return success_response(facility.model_dump(mode="json"), request_id=_rid(request))


@router.post(
    "/organisations/{tenant_id}/facilities/{facility_id}/reactivate",
    response_model=ApiResponse,
    summary="Reactivate a facility",
    dependencies=[Depends(_limit)],
)
async def reactivate_facility(
    tenant_id: uuid.UUID,
    facility_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    operator: User = Depends(require_platform_operator),
):
    facility = await service.set_facility_status(db, tenant_id, facility_id, operator, active=True, reason=None)
    return success_response(facility.model_dump(mode="json"), request_id=_rid(request))


@router.post(
    "/organisations/{tenant_id}/administrators",
    response_model=ApiResponse,
    status_code=201,
    summary="Assign a Hospital Admin to an organisation (audited; one-time activation link)",
    dependencies=[Depends(_limit)],
)
async def assign_administrator(
    tenant_id: uuid.UUID,
    payload: AssignAdministratorRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    operator: User = Depends(require_platform_operator),
):
    result = await service.assign_administrator(db, tenant_id, payload, operator)
    return success_response(result.model_dump(mode="json"), request_id=_rid(request))
