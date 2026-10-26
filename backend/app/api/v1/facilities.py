import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permissions
from app.core.responses import ApiResponse, success_response
from app.modules.auth.models import User
from app.modules.facilities import service
from app.modules.facilities.schemas import FacilityCreateRequest, FacilityUpdateRequest, StatusChangeRequest

router = APIRouter(prefix="/facilities", tags=["facilities"])


@router.get("", response_model=ApiResponse, summary="List facilities in the current tenant")
async def list_facilities(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("facilities.manage")),
):
    facilities = await service.list_facilities(db, current_user)
    return success_response(
        [facility.model_dump(mode="json") for facility in facilities],
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/{facility_id}", response_model=ApiResponse, summary="Get a single facility")
async def get_facility(
    facility_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("facilities.manage")),
):
    facility = await service.get_facility(db, facility_id, current_user)
    return success_response(
        facility.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("", response_model=ApiResponse, summary="Create a facility in the current tenant")
async def create_facility(
    payload: FacilityCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("facilities.manage")),
):
    facility = await service.create_facility(db, payload, current_user)
    return success_response(
        facility.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.patch("/{facility_id}", response_model=ApiResponse, summary="Update a facility")
async def update_facility(
    facility_id: uuid.UUID,
    payload: FacilityUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("facilities.manage")),
):
    facility = await service.update_facility(db, facility_id, payload, current_user)
    return success_response(
        facility.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/{facility_id}/deactivate",
    response_model=ApiResponse,
    summary="Deactivate a facility (blocked while it has open clinical work)",
)
async def deactivate_facility(
    facility_id: uuid.UUID,
    payload: StatusChangeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("facilities.manage")),
):
    facility = await service.deactivate_facility(db, facility_id, payload.reason, current_user)
    return success_response(
        facility.model_dump(mode="json"), request_id=getattr(request.state, "request_id", None)
    )


@router.post("/{facility_id}/reactivate", response_model=ApiResponse, summary="Reactivate a facility")
async def reactivate_facility(
    facility_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("facilities.manage")),
):
    facility = await service.reactivate_facility(db, facility_id, current_user)
    return success_response(
        facility.model_dump(mode="json"), request_id=getattr(request.state, "request_id", None)
    )
