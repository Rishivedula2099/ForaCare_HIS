import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permissions
from app.core.responses import ApiResponse, success_response
from app.modules.abdm import service
from app.modules.abdm.factory import get_abdm_adapter
from app.modules.abdm.schemas import ConsentCreateRequest, OtpRequest, VerifyRequest
from app.modules.auth.models import User

router = APIRouter(prefix="/abdm", tags=["abdm"])


def _ok(request: Request, data):
    payload = data.model_dump(mode="json") if hasattr(data, "model_dump") else data
    return success_response(payload, request_id=getattr(request.state, "request_id", None))


@router.get("/status", response_model=ApiResponse, summary="ABDM gateway connection status")
async def abdm_status(
    request: Request,
    current_user: User = Depends(require_permissions("patients.view")),
):
    status = await get_abdm_adapter().check_connection()
    return _ok(request, {"mode": status.mode, "connected": status.connected, "message": status.message})


@router.post("/otp", response_model=ApiResponse, summary="Start ABHA OTP verification")
async def request_otp(
    payload: OtpRequest,
    request: Request,
    current_user: User = Depends(require_permissions("patients.link_abha")),
):
    return _ok(request, await service.request_otp(payload.auth_method, payload.identifier))


@router.get(
    "/patients/{patient_id}/abha", response_model=ApiResponse, summary="A patient's ABHA status and consents"
)
async def get_abha_status(
    patient_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("patients.view")),
):
    return _ok(request, await service.get_status(db, patient_id, current_user))


@router.post(
    "/patients/{patient_id}/abha/verify", response_model=ApiResponse, summary="Verify OTP and record the ABHA"
)
async def verify_abha(
    patient_id: uuid.UUID,
    payload: VerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("patients.link_abha")),
):
    return _ok(
        request,
        await service.verify(
            db, patient_id, current_user, transaction_id=payload.transaction_id, otp=payload.otp
        ),
    )


@router.post(
    "/patients/{patient_id}/abha/link", response_model=ApiResponse, summary="Link a verified ABHA to the patient"
)
async def link_abha(
    patient_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("patients.link_abha")),
):
    return _ok(request, await service.link(db, patient_id, current_user))


@router.delete("/patients/{patient_id}/abha", response_model=ApiResponse, summary="Unlink the patient's ABHA")
async def unlink_abha(
    patient_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("patients.unlink_abha")),
):
    return _ok(request, await service.unlink(db, patient_id, current_user))


@router.post("/patients/{patient_id}/abha/consents", response_model=ApiResponse, summary="Record ABDM consent")
async def grant_consent(
    patient_id: uuid.UUID,
    payload: ConsentCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("patients.link_abha")),
):
    return _ok(request, await service.grant_consent(db, patient_id, current_user, purpose=payload.purpose))


@router.post(
    "/patients/{patient_id}/abha/consents/{consent_id}/revoke",
    response_model=ApiResponse,
    summary="Revoke ABDM consent",
)
async def revoke_consent(
    patient_id: uuid.UUID,
    consent_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("patients.link_abha")),
):
    return _ok(request, await service.revoke_consent(db, patient_id, consent_id, current_user))
