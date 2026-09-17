import logging
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cookies import ACCESS_COOKIE_NAME
from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.permissions import authenticate_by_access_token, require_permissions
from app.core.responses import ApiResponse, success_response
from app.modules.auth.models import User
from app.modules.opd import service
from app.modules.opd.schemas import (
    ConsultationCreateRequest,
    ConsultationUpdateRequest,
    EncounterCreateRequest,
    PrescriptionCreateRequest,
    PrescriptionUpdateRequest,
    QRVerifyRequest,
    TokenStatusUpdateRequest,
)
from app.modules.opd.ws_manager import manager as queue_ws_manager

router = APIRouter(prefix="/opd", tags=["opd"])
logger = logging.getLogger(__name__)


@router.post("/encounters", response_model=ApiResponse, summary="Register an OPD visit (walk-in or appointment)")
async def register_visit(
    payload: EncounterCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("opd.manage_queue")),
):
    encounter = await service.register_visit(db, payload, current_user)
    return success_response(
        encounter.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/encounters", response_model=ApiResponse, summary="List/search OPD encounters in the current facility")
async def list_encounters(
    request: Request,
    patient_id: uuid.UUID | None = None,
    doctor_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    visit_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("opd.view")),
):
    encounters = await service.list_encounters(
        db,
        current_user,
        patient_id=patient_id,
        doctor_id=doctor_id,
        department_id=department_id,
        visit_date=visit_date,
    )
    return success_response(
        [encounter.model_dump(mode="json") for encounter in encounters],
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/encounters/{encounter_id}", response_model=ApiResponse, summary="Get a single OPD encounter")
async def get_encounter(
    encounter_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("opd.view")),
):
    encounter = await service.get_encounter(db, encounter_id, current_user)
    return success_response(
        encounter.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/doctors/{doctor_id}/queue",
    response_model=ApiResponse,
    summary="Get a doctor's OPD queue (tokens) for a given day",
)
async def get_doctor_queue(
    doctor_id: uuid.UUID,
    request: Request,
    queue_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("opd.view")),
):
    encounters = await service.get_doctor_queue(
        db, current_user, doctor_id, queue_date or date.today()
    )
    return success_response(
        [encounter.model_dump(mode="json") for encounter in encounters],
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/doctors/{doctor_id}/queue/call-next",
    response_model=ApiResponse,
    summary="Call the next waiting token in a doctor's queue",
)
async def call_next_token(
    doctor_id: uuid.UUID,
    request: Request,
    queue_date: date | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("opd.manage_queue")),
):
    encounter = await service.call_next_token(
        db, current_user, doctor_id, queue_date or date.today()
    )
    return success_response(
        encounter.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.patch(
    "/tokens/{token_id}/status",
    response_model=ApiResponse,
    summary="Transition a token's status (call, start, complete, skip, cancel, re-queue)",
)
async def update_token_status(
    token_id: uuid.UUID,
    payload: TokenStatusUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("opd.manage_queue")),
):
    encounter = await service.update_token_status(db, current_user, token_id, payload.status)
    return success_response(
        encounter.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/encounters/{encounter_id}/qr/revoke",
    response_model=ApiResponse,
    summary="Revoke an encounter's check-in QR code",
)
async def revoke_qr(
    encounter_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("opd.manage_queue")),
):
    encounter = await service.revoke_qr(db, current_user, encounter_id)
    return success_response(
        encounter.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/qr/verify",
    response_model=ApiResponse,
    summary="Verify a scanned/entered OPD check-in QR code",
)
async def verify_qr(
    payload: QRVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("opd.view")),
):
    result = await service.verify_qr_code(db, current_user, payload.qr_code)
    return success_response(
        result.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/encounters/{encounter_id}/consultation",
    response_model=ApiResponse,
    summary="Create the consultation record for an encounter",
)
async def create_consultation(
    encounter_id: uuid.UUID,
    payload: ConsultationCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("consultations.manage")),
):
    consultation = await service.create_consultation(db, current_user, encounter_id, payload)
    return success_response(
        consultation.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/encounters/{encounter_id}/consultation",
    response_model=ApiResponse,
    summary="Get the consultation record for an encounter",
)
async def get_consultation(
    encounter_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("consultations.view")),
):
    consultation = await service.get_consultation(db, current_user, encounter_id)
    return success_response(
        consultation.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.patch(
    "/encounters/{encounter_id}/consultation",
    response_model=ApiResponse,
    summary="Update the consultation record for an encounter",
)
async def update_consultation(
    encounter_id: uuid.UUID,
    payload: ConsultationUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("consultations.manage")),
):
    consultation = await service.update_consultation(db, current_user, encounter_id, payload)
    return success_response(
        consultation.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/patients/{patient_id}/consultations",
    response_model=ApiResponse,
    summary="Retrieve a patient's OPD consultation history",
)
async def list_patient_consultation_history(
    patient_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("consultations.view")),
):
    consultations = await service.list_patient_consultation_history(db, current_user, patient_id)
    return success_response(
        [consultation.model_dump(mode="json") for consultation in consultations],
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/encounters/{encounter_id}/prescription",
    response_model=ApiResponse,
    summary="Create the prescription for an encounter",
)
async def create_prescription(
    encounter_id: uuid.UUID,
    payload: PrescriptionCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("prescriptions.manage")),
):
    prescription = await service.create_prescription(db, current_user, encounter_id, payload)
    return success_response(
        prescription.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.get(
    "/encounters/{encounter_id}/prescription",
    response_model=ApiResponse,
    summary="Get the prescription for an encounter",
)
async def get_prescription(
    encounter_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("prescriptions.view")),
):
    prescription = await service.get_prescription(db, current_user, encounter_id)
    return success_response(
        prescription.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.patch(
    "/encounters/{encounter_id}/prescription",
    response_model=ApiResponse,
    summary="Update the prescription for an encounter",
)
async def update_prescription(
    encounter_id: uuid.UUID,
    payload: PrescriptionUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("prescriptions.manage")),
):
    prescription = await service.update_prescription(db, current_user, encounter_id, payload)
    return success_response(
        prescription.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.websocket("/doctors/{doctor_id}/queue/ws")
async def doctor_queue_ws(
    websocket: WebSocket,
    doctor_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Push channel for P3-B03 "queue updates" - sends `{"type":
    "queue_updated"}` whenever this doctor's queue changes (registration,
    call-next, or any token status transition). Carries no queue data
    itself; clients react by refetching `GET /opd/doctors/{id}/queue`,
    which stays the single source of truth for the queue's shape.

    Auth mirrors `get_current_user`/`require_permissions` but reads the
    cookie from `WebSocket.cookies` (a plain `Depends` chain built for HTTP
    requests doesn't apply to WebSocket routes), and fails by closing the
    socket with a policy-violation code rather than raising an HTTP error.
    """
    try:
        current_user = await authenticate_by_access_token(websocket.cookies.get(ACCESS_COOKIE_NAME), db)
        if "opd.view" not in {permission.code for permission in current_user.role.permissions}:
            raise AppError("Forbidden", code="FORBIDDEN")
        await service.get_doctor_for_queue_access(db, current_user, doctor_id)
    except Exception:
        await websocket.close(code=4403)
        return

    await websocket.accept()
    doctor_key = str(doctor_id)
    await queue_ws_manager.connect(doctor_key, websocket)
    try:
        while True:
            # Clients don't need to send anything; this just keeps the
            # coroutine alive to detect disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.warning("OPD queue websocket for doctor %s ended unexpectedly", doctor_id, exc_info=True)
    finally:
        await queue_ws_manager.disconnect(doctor_key, websocket)
