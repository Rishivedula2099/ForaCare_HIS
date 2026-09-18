import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permissions
from app.core.responses import ApiResponse, success_response
from app.modules.auth.models import User
from app.modules.ipd import service
from app.modules.ipd.schemas import (
    AdmissionCreateRequest,
    BedCreateRequest,
    BedUpdateRequest,
    ConsentCreateRequest,
    DischargeCreateRequest,
    RoomCreateRequest,
    RoomUpdateRequest,
    TransferCreateRequest,
    WardCreateRequest,
    WardUpdateRequest,
)

router = APIRouter(prefix="/ipd", tags=["ipd"])


# ---------------------------------------------------------------------------
# Ward
# ---------------------------------------------------------------------------


@router.get("/wards", response_model=ApiResponse, summary="List wards in the current facility")
async def list_wards(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ipd.view")),
):
    wards = await service.list_wards(db, current_user)
    return success_response(
        [ward.model_dump(mode="json") for ward in wards],
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/wards", response_model=ApiResponse, summary="Create a ward")
async def create_ward(
    payload: WardCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ipd.manage_beds")),
):
    ward = await service.create_ward(db, payload, current_user)
    return success_response(
        ward.model_dump(mode="json"), request_id=getattr(request.state, "request_id", None)
    )


@router.patch("/wards/{ward_id}", response_model=ApiResponse, summary="Update a ward")
async def update_ward(
    ward_id: uuid.UUID,
    payload: WardUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ipd.manage_beds")),
):
    ward = await service.update_ward(db, ward_id, payload, current_user)
    return success_response(
        ward.model_dump(mode="json"), request_id=getattr(request.state, "request_id", None)
    )


# ---------------------------------------------------------------------------
# Room
# ---------------------------------------------------------------------------


@router.get("/rooms", response_model=ApiResponse, summary="List rooms in the current facility")
async def list_rooms(
    request: Request,
    ward_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ipd.view")),
):
    rooms = await service.list_rooms(db, current_user, ward_id=ward_id)
    return success_response(
        [room.model_dump(mode="json") for room in rooms],
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/rooms", response_model=ApiResponse, summary="Create a room")
async def create_room(
    payload: RoomCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ipd.manage_beds")),
):
    room = await service.create_room(db, payload, current_user)
    return success_response(
        room.model_dump(mode="json"), request_id=getattr(request.state, "request_id", None)
    )


@router.patch("/rooms/{room_id}", response_model=ApiResponse, summary="Update a room")
async def update_room(
    room_id: uuid.UUID,
    payload: RoomUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ipd.manage_beds")),
):
    room = await service.update_room(db, room_id, payload, current_user)
    return success_response(
        room.model_dump(mode="json"), request_id=getattr(request.state, "request_id", None)
    )


# ---------------------------------------------------------------------------
# Bed
# ---------------------------------------------------------------------------


@router.get("/beds", response_model=ApiResponse, summary="List/filter beds (the bed board)")
async def list_beds(
    request: Request,
    ward_id: uuid.UUID | None = None,
    room_id: uuid.UUID | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ipd.view")),
):
    beds = await service.list_beds(db, current_user, ward_id=ward_id, room_id=room_id, status=status)
    return success_response(
        [bed.model_dump(mode="json") for bed in beds],
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/beds", response_model=ApiResponse, summary="Create a bed")
async def create_bed(
    payload: BedCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ipd.manage_beds")),
):
    bed = await service.create_bed(db, payload, current_user)
    return success_response(
        bed.model_dump(mode="json"), request_id=getattr(request.state, "request_id", None)
    )


@router.patch("/beds/{bed_id}", response_model=ApiResponse, summary="Update a bed (e.g. status override)")
async def update_bed(
    bed_id: uuid.UUID,
    payload: BedUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ipd.manage_beds")),
):
    bed = await service.update_bed(db, bed_id, payload, current_user)
    return success_response(
        bed.model_dump(mode="json"), request_id=getattr(request.state, "request_id", None)
    )


# ---------------------------------------------------------------------------
# Admission
# ---------------------------------------------------------------------------


@router.post("/admissions", response_model=ApiResponse, summary="Admit a patient into a bed")
async def create_admission(
    payload: AdmissionCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ipd.manage_beds")),
):
    admission = await service.create_admission(db, payload, current_user)
    return success_response(
        admission.model_dump(mode="json"), request_id=getattr(request.state, "request_id", None)
    )


@router.get("/admissions", response_model=ApiResponse, summary="List/search admissions")
async def list_admissions(
    request: Request,
    patient_id: uuid.UUID | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ipd.view")),
):
    admissions = await service.list_admissions(db, current_user, patient_id=patient_id, status=status)
    return success_response(
        [admission.model_dump(mode="json") for admission in admissions],
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/admissions/{admission_id}", response_model=ApiResponse, summary="Get a single admission")
async def get_admission(
    admission_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ipd.view")),
):
    admission = await service.get_admission(db, admission_id, current_user)
    return success_response(
        admission.model_dump(mode="json"), request_id=getattr(request.state, "request_id", None)
    )


@router.post(
    "/admissions/{admission_id}/transfer",
    response_model=ApiResponse,
    summary="Transfer an admitted patient to a different bed",
)
async def create_transfer(
    admission_id: uuid.UUID,
    payload: TransferCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ipd.manage_beds")),
):
    transfer = await service.create_transfer(db, admission_id, payload, current_user)
    return success_response(
        transfer.model_dump(mode="json"), request_id=getattr(request.state, "request_id", None)
    )


@router.post(
    "/admissions/{admission_id}/discharge",
    response_model=ApiResponse,
    summary="Discharge a patient and free their bed",
)
async def create_discharge(
    admission_id: uuid.UUID,
    payload: DischargeCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ipd.manage_beds")),
):
    discharge = await service.create_discharge(db, admission_id, payload, current_user)
    return success_response(
        discharge.model_dump(mode="json"), request_id=getattr(request.state, "request_id", None)
    )


@router.get(
    "/admissions/{admission_id}/consents",
    response_model=ApiResponse,
    summary="List consents recorded for an admission",
)
async def list_consents(
    admission_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ipd.view")),
):
    consents = await service.list_consents(db, admission_id, current_user)
    return success_response(
        [consent.model_dump(mode="json") for consent in consents],
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/admissions/{admission_id}/consents",
    response_model=ApiResponse,
    summary="Record a consent for an admission",
)
async def create_consent(
    admission_id: uuid.UUID,
    payload: ConsentCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("ipd.manage_beds")),
):
    consent = await service.create_consent(db, admission_id, payload, current_user)
    return success_response(
        consent.model_dump(mode="json"), request_id=getattr(request.state, "request_id", None)
    )
