import uuid

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permissions
from app.core.responses import ApiResponse, success_response
from app.modules.files import service as files_service
from app.modules.auth.models import User
from app.modules.patients import service
from app.modules.patients.schemas import (
    DuplicateCheckRequest,
    PatientCreateRequest,
    PatientUpdateRequest,
)

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("", response_model=ApiResponse, summary="List/search patients in the current facility")
async def list_patients(
    request: Request,
    uid: str | None = None,
    mrn: str | None = None,
    name: str | None = None,
    mobile: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("patients.view")),
):
    patients = await service.list_patients(
        db, current_user, uid=uid, mrn=mrn, name=name, mobile=mobile
    )
    return success_response(
        [patient.model_dump(mode="json") for patient in patients],
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/check-duplicates",
    response_model=ApiResponse,
    summary="Check for possible duplicate patients before registration",
)
async def check_duplicates(
    payload: DuplicateCheckRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("patients.manage")),
):
    duplicates = await service.find_duplicate_patients(
        db,
        current_user.tenant_id,
        mobile=payload.mobile,
        id_number=payload.id_number,
        first_name=payload.first_name,
        last_name=payload.last_name,
        dob=payload.dob,
    )
    return success_response(
        [patient.model_dump(mode="json") for patient in duplicates],
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


@router.patch("/{patient_id}", response_model=ApiResponse, summary="Update a patient's record")
async def update_patient(
    patient_id: uuid.UUID,
    payload: PatientUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("patients.manage")),
):
    patient = await service.update_patient(db, patient_id, payload, current_user)
    return success_response(
        patient.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/{patient_id}/photo", response_model=ApiResponse, summary="Upload a patient's photo"
)
async def upload_patient_photo(
    patient_id: uuid.UUID,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("patients.manage")),
):
    raw_bytes = await file.read()
    photo = await service.upload_patient_photo(
        db,
        patient_id,
        current_user,
        content_type=file.content_type,
        raw_bytes=raw_bytes,
    )
    return success_response(
        {
            "id": str(photo.id),
            "content_type": photo.content_type,
            "is_primary": photo.is_primary,
            "captured_at": photo.captured_at.isoformat(),
        },
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/{patient_id}/photo/{photo_id}", summary="Retrieve a patient's photo file")
async def get_patient_photo(
    patient_id: uuid.UUID,
    photo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("patients.view")),
):
    photo = await service.get_patient_photo_file(db, patient_id, photo_id, current_user)
    absolute_path = files_service.resolve_absolute_path(photo.storage_path)
    return FileResponse(absolute_path, media_type=photo.content_type)
