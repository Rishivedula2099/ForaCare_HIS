"""P10-F01: unauthenticated endpoints backing the public landing page.

Deliberately tiny: they accept an enquiry and return nothing about the
system, tenants, patients or staff."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.core.responses import ApiResponse, success_response
from app.modules.audit import service as audit_service
from app.modules.onboarding.models import OnboardingRequest
from app.modules.onboarding.schemas import OnboardingRequestCreate

router = APIRouter(prefix="/public", tags=["public"])


@router.post(
    "/onboarding-requests",
    response_model=ApiResponse,
    summary="Request onboarding for a hospital or clinic",
    dependencies=[Depends(rate_limit("onboarding-request", limit=max(3, get_settings().rate_limit_public_per_minute // 6)))],
)
async def create_onboarding_request(
    payload: OnboardingRequestCreate, request: Request, db: AsyncSession = Depends(get_db)
):
    request_id = getattr(request.state, "request_id", None)
    # Bots get the same answer but nothing is stored.
    if not payload.website:
        enquiry = OnboardingRequest(
            organization_name=payload.organization_name.strip(),
            contact_name=payload.contact_name.strip(),
            email=str(payload.email).lower(),
            phone=payload.phone.strip() if payload.phone else None,
            facility_type=payload.facility_type,
            message=payload.message.strip() if payload.message else None,
        )
        db.add(enquiry)
        await db.flush()
        await audit_service.record_event(
            db,
            action="onboarding.request_received",
            resource_type="onboarding_request",
            resource_id=enquiry.id,
            actor_username="public",
        )
    return success_response({"received": True}, request_id=request_id)
