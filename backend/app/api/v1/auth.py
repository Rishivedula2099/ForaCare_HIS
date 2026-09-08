from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import NotFoundError
from app.core.permissions import get_current_user
from app.core.responses import ApiResponse, success_response
from app.modules.audit import service as audit_service
from app.modules.auth import service
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    MeResponse,
    RefreshRequest,
    TokenResponse,
    UserOut,
)
from app.modules.facilities.models import Facility
from app.modules.tenants.models import Tenant

router = APIRouter(prefix="/auth", tags=["auth"])


async def _load_context(db: AsyncSession, user: User) -> tuple[Tenant, Facility]:
    tenant = (await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))).scalar_one_or_none()
    facility = (
        await db.execute(select(Facility).where(Facility.id == user.facility_id))
    ).scalar_one_or_none()

    if tenant is None or facility is None:
        raise NotFoundError("Tenant or facility context for this user could not be found.")

    return tenant, facility


@router.post("/login", response_model=ApiResponse, summary="Authenticate with username and password")
async def login(payload: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    user = await service.authenticate_user(db, payload.username, payload.password)
    tenant, facility = await _load_context(db, user)
    tokens = await service.issue_tokens(db, user)

    await audit_service.record_event(
        db,
        action="auth.login.succeeded",
        resource_type="user",
        resource_id=user.id,
        actor_user_id=user.id,
        actor_username=user.username,
        tenant_id=user.tenant_id,
        facility_id=user.facility_id,
    )

    response = LoginResponse(
        user=UserOut.from_user(user), tenant=tenant, facility=facility, tokens=tokens
    )
    return success_response(
        response.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/refresh", response_model=ApiResponse, summary="Exchange a refresh token for a new token pair")
async def refresh(payload: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    tokens = await service.rotate_refresh_token(db, payload.refresh_token)
    return success_response(
        tokens.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/logout", response_model=ApiResponse, summary="Invalidate the given refresh token")
async def logout(payload: LogoutRequest, request: Request, db: AsyncSession = Depends(get_db)):
    token = await service.revoke_refresh_token(db, payload.refresh_token)
    if token is not None:
        await audit_service.record_event(
            db,
            action="auth.logout",
            resource_type="user",
            resource_id=token.user_id,
            actor_user_id=token.user_id,
        )
    return success_response(
        {"logged_out": True},
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/me", response_model=ApiResponse, summary="Fetch the current authenticated user context")
async def me(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tenant, facility = await _load_context(db, current_user)
    response = MeResponse(user=UserOut.from_user(current_user), tenant=tenant, facility=facility)
    return success_response(
        response.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/change-password", response_model=ApiResponse, summary="Change the current user's password")
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.change_password(db, current_user, payload.current_password, payload.new_password)
    await audit_service.record_event(
        db,
        action="auth.password_changed",
        resource_type="user",
        resource_id=current_user.id,
    )
    return success_response(
        {"changed": True},
        request_id=getattr(request.state, "request_id", None),
    )
