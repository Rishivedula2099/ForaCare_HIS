from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.cookies import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME, clear_auth_cookies, set_auth_cookies
from app.core.database import get_db
from app.core.exceptions import NotFoundError, UnauthorizedError
from app.core.permissions import get_current_user
from app.core.responses import ApiResponse, success_response
from app.modules.audit import service as audit_service
from app.modules.auth import service
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
    OtpRequestedResponse,
    RequestEmailChangeRequest,
    RequestPhoneChangeRequest,
    SessionMeta,
    UserOut,
    VerifyEmailChangeRequest,
    VerifyPhoneChangeRequest,
)
from app.modules.doctors.models import Doctor
from app.modules.facilities.models import Facility
from app.modules.tenants.models import Tenant

router = APIRouter(prefix="/auth", tags=["auth"])


async def _find_linked_doctor_id(db: AsyncSession, user: User):
    result = await db.execute(select(Doctor.id).where(Doctor.user_id == user.id))
    return result.scalar_one_or_none()


async def _load_context(db: AsyncSession, user: User) -> tuple[Tenant, Facility]:
    tenant = (await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))).scalar_one_or_none()
    facility = (
        await db.execute(select(Facility).where(Facility.id == user.facility_id))
    ).scalar_one_or_none()

    if tenant is None or facility is None:
        raise NotFoundError("Tenant or facility context for this user could not be found.")

    return tenant, facility


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent")
    return ip_address, user_agent


@router.post("/login", response_model=ApiResponse, summary="Authenticate with username and password")
async def login(
    payload: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    user = await service.authenticate_user(db, payload.username, payload.password)
    tenant, facility = await _load_context(db, user)

    ip_address, user_agent = _client_meta(request)
    tokens = await service.issue_tokens(db, user, ip_address=ip_address, user_agent=user_agent)

    settings = get_settings()
    set_auth_cookies(
        response,
        settings=settings,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        access_max_age=settings.access_token_expire_minutes * 60,
        refresh_max_age=settings.refresh_token_expire_days * 86400,
    )

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

    doctor_id = await _find_linked_doctor_id(db, user)
    body = LoginResponse(
        user=UserOut.from_user(user, doctor_id=doctor_id),
        tenant=tenant,
        facility=facility,
        session=SessionMeta(expires_in=settings.access_token_expire_minutes * 60),
    )
    return success_response(
        body.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/refresh", response_model=ApiResponse, summary="Rotate the session's refresh cookie for a new pair"
)
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh_token:
        raise UnauthorizedError("Not authenticated.")

    ip_address, user_agent = _client_meta(request)
    tokens = await service.rotate_session(
        db, raw_refresh_token, ip_address=ip_address, user_agent=user_agent
    )

    settings = get_settings()
    set_auth_cookies(
        response,
        settings=settings,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        access_max_age=settings.access_token_expire_minutes * 60,
        refresh_max_age=settings.refresh_token_expire_days * 86400,
    )

    return success_response(
        SessionMeta(expires_in=settings.access_token_expire_minutes * 60).model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/logout", response_model=ApiResponse, summary="End the current session")
async def logout(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    access_token = request.cookies.get(ACCESS_COOKIE_NAME)
    session_id = None
    if access_token:
        try:
            claims, session = await service.get_session_for_access_token(db, access_token)
            session_id = session.id
        except UnauthorizedError:
            session_id = None

    if session_id is not None:
        session = await service.revoke_session_by_id(db, session_id)
        if session is not None:
            await audit_service.record_event(
                db,
                action="auth.logout",
                resource_type="user_session",
                resource_id=session.id,
                actor_user_id=session.user_id,
            )

    clear_auth_cookies(response, settings=get_settings())
    return success_response(
        {"logged_out": True},
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/logout-all", response_model=ApiResponse, summary="End every active session for this user")
async def logout_all(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await service.revoke_all_sessions_for_user(db, current_user.id)
    await audit_service.record_event(
        db,
        action="auth.logout_all",
        resource_type="user",
        resource_id=current_user.id,
    )
    clear_auth_cookies(response, settings=get_settings())
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
    doctor_id = await _find_linked_doctor_id(db, current_user)
    response = MeResponse(
        user=UserOut.from_user(current_user, doctor_id=doctor_id), tenant=tenant, facility=facility
    )
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


@router.post(
    "/email/change/request", response_model=ApiResponse, summary="Request an OTP to change account email"
)
async def request_email_change(
    payload: RequestEmailChangeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = get_settings()
    debug_code = await service.request_email_change(db, current_user, payload.new_email)
    return success_response(
        OtpRequestedResponse(
            expires_in_minutes=settings.otp_expire_minutes, debug_code=debug_code
        ).model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/email/change/verify", response_model=ApiResponse, summary="Verify OTP and apply the new email"
)
async def verify_email_change(
    payload: VerifyEmailChangeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    before_email = current_user.email
    await service.verify_email_change(db, current_user, payload.new_email, payload.code)
    await audit_service.record_event(
        db,
        action="auth.email_changed",
        resource_type="user",
        resource_id=current_user.id,
        before={"email": before_email},
        after={"email": payload.new_email},
    )
    return success_response(
        {"changed": True},
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/phone/change/request", response_model=ApiResponse, summary="Request an OTP to change account phone"
)
async def request_phone_change(
    payload: RequestPhoneChangeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    settings = get_settings()
    debug_code = await service.request_phone_change(db, current_user, payload.new_phone)
    return success_response(
        OtpRequestedResponse(
            expires_in_minutes=settings.otp_expire_minutes, debug_code=debug_code
        ).model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/phone/change/verify", response_model=ApiResponse, summary="Verify OTP and apply the new phone number"
)
async def verify_phone_change(
    payload: VerifyPhoneChangeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    before_phone = current_user.phone
    await service.verify_phone_change(db, current_user, payload.new_phone, payload.code)
    await audit_service.record_event(
        db,
        action="auth.phone_changed",
        resource_type="user",
        resource_id=current_user.id,
        before={"phone": before_phone},
        after={"phone": payload.new_phone},
    )
    return success_response(
        {"changed": True},
        request_id=getattr(request.state, "request_id", None),
    )
