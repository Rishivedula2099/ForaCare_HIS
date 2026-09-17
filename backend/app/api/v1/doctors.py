import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permissions
from app.core.responses import ApiResponse, success_response
from app.modules.auth.models import User
from app.modules.doctors import service
from app.modules.doctors.schemas import DoctorCreateRequest, DoctorUpdateRequest

router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.get("", response_model=ApiResponse, summary="List/search doctors in the current facility")
async def list_doctors(
    request: Request,
    name: str | None = None,
    department_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("doctors.view")),
):
    doctors = await service.list_doctors(db, current_user, name=name, department_id=department_id)
    return success_response(
        [doctor.model_dump(mode="json") for doctor in doctors],
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/{doctor_id}", response_model=ApiResponse, summary="Get a single doctor")
async def get_doctor(
    doctor_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("doctors.view")),
):
    doctor = await service.get_doctor(db, doctor_id, current_user)
    return success_response(
        doctor.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("", response_model=ApiResponse, summary="Create a doctor in the current facility")
async def create_doctor(
    payload: DoctorCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("doctors.manage")),
):
    doctor = await service.create_doctor(db, payload, current_user)
    return success_response(
        doctor.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.patch("/{doctor_id}", response_model=ApiResponse, summary="Update a doctor")
async def update_doctor(
    doctor_id: uuid.UUID,
    payload: DoctorUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("doctors.manage")),
):
    doctor = await service.update_doctor(db, doctor_id, payload, current_user)
    return success_response(
        doctor.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )
