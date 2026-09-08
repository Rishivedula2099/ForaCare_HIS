import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permissions
from app.core.responses import ApiResponse, success_response
from app.modules.auth.models import User
from app.modules.patients import service
from app.modules.patients.schemas import PatientCreateRequest

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=ApiResponse, summary="List patients in the current tenant")
async def list_patients(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("patients.view")),
):
    patients = await service.list_patients(db, current_user)
    return success_response(
        [patient.model_dump(mode="json") for patient in patients],
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/{patient_id}", response_model=ApiResponse, summary="Get a single patient (Patient 360)")
async def get_patient(
    patient_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("patients.view")),
):
    patient = await service.get_patient(db, patient_id, current_user)
    return success_response(
        patient.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("", response_model=ApiResponse, summary="Register a new patient in the current tenant")
async def create_patient(
    payload: PatientCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("patients.manage")),
):
    patient = await service.create_patient(db, payload, current_user)
    return success_response(
        patient.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )
