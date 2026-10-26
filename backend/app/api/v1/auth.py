from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import set_committed_value

from app.core.config import get_settings
from app.core.context import set_tenant_context
from app.core.cookies import ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME, clear_auth_cookies, set_auth_cookies
from app.core.database import get_db
from app.core.exceptions import NotFoundError, UnauthorizedError
from app.core.permissions import get_current_user
from app.core.rate_limit import check_rate_limit, client_ip, rate_limit
from app.core.responses import ApiResponse, success_response
from app.modules.audit import service as audit_service
from app.modules.auth import mailer, service, user_tokens
from app.modules.auth.models import User
from app.modules.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    MeResponse,
    OtpRequestedResponse,
    PasswordResetRequest,
    PasswordResetRequestedResponse,
    SetPasswordWithTokenRequest,
    SwitchFacilityRequest,
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

# P9-B01: brute-force / abuse guards. Evaluated at import so the limits come
# from settings; per-IP for every route, plus per-username on login below.
_settings = get_settings()
_limit_refresh = rate_limit("auth-refresh", limit=_settings.rate_limit_login_per_minute * 3)
_limit_sensitive = rate_limit("auth-sensitive", limit=_settings.rate_limit_sensitive_per_minute)


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
    limit = get_settings().rate_limit_login_per_minute
    check_rate_limit(f"login-ip:{client_ip(request)}", limit=limit * 3, window_seconds=60)
    # Per-account budget stops a distributed guess against one username.
    check_rate_limit(f"login-user:{payload.username.lower()}", limit=limit, window_seconds=60)
    try:
        user = await service.authenticate_user(db, payload.username, payload.password)
        facility, facilities = await service.resolve_login_facility(db, user, payload.facility_id)
    except UnauthorizedError as exc:
        await service.record_login_failure(
            db, payload.username, exc, ip_address=client_ip(request)
        )
        raise
    tenant = (await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))).scalar_one()

    ip_address, user_agent = _client_meta(request)
    tokens = await service.issue_tokens(
        db, user, facility_id=facility.id, ip_address=ip_address, user_agent=user_agent
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

    await audit_service.record_event(
        db,
        action="auth.login.succeeded",
        resource_type="user",
        resource_id=user.id,
        actor_user_id=user.id,
        actor_username=user.username,
        tenant_id=user.tenant_id,
        facility_id=facility.id,
    )

    doctor_id = await _find_linked_doctor_id(db, user)
    # The session's facility (not the user's home facility) is the active one.
    set_committed_value(user, "facility_id", facility.id)
    body = LoginResponse(
        user=UserOut.from_user(user, doctor_id=doctor_id),
        tenant=tenant,
        facility=facility,
        facilities=facilities,
        session=SessionMeta(expires_in=settings.access_token_expire_minutes * 60),
    )
    return success_response(
        body.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/refresh", response_model=ApiResponse, summary="Rotate the session's refresh cookie for a new pair",
    dependencies=[Depends(_limit_refresh)],
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
        user=UserOut.from_user(current_user, doctor_id=doctor_id),
        tenant=tenant,
        facility=facility,
        facilities=await service.list_user_facilities(db, current_user),
    )
    return success_response(
        response.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post(
    "/change-password",
    response_model=ApiResponse,
    summary="Change the current user's password",
    dependencies=[Depends(_limit_sensitive)],
)
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
    "/email/change/request", response_model=ApiResponse, summary="Request an OTP to change account email",
    dependencies=[Depends(_limit_sensitive)],
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
    "/email/change/verify", response_model=ApiResponse, summary="Verify OTP and apply the new email",
    dependencies=[Depends(_limit_sensitive)],
)
async def verify_email_change(
    payload: VerifyEmailChangeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    before_email = current_user.email
    try:
        await service.verify_email_change(db, current_user, payload.new_email, payload.code)
    except UnauthorizedError:
        await audit_service.record_event(
            db,
            action="auth.otp.verification_failed",
            resource_type="user",
            resource_id=current_user.id,
            after={"purpose": "email_change"},
        )
        raise
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
    "/phone/change/request", response_model=ApiResponse, summary="Request an OTP to change account phone",
    dependencies=[Depends(_limit_sensitive)],
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
    "/phone/change/verify", response_model=ApiResponse, summary="Verify OTP and apply the new phone number",
    dependencies=[Depends(_limit_sensitive)],
)
async def verify_phone_change(
    payload: VerifyPhoneChangeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    before_phone = current_user.phone
    try:
        await service.verify_phone_change(db, current_user, payload.new_phone, payload.code)
    except UnauthorizedError:
        await audit_service.record_event(
            db,
            action="auth.otp.verification_failed",
            resource_type="user",
            resource_id=current_user.id,
            after={"purpose": "phone_change"},
        )
        raise
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


@router.post(
    "/switch-facility",
    response_model=ApiResponse,
    summary="Switch the session to another facility the user belongs to",
    dependencies=[Depends(_limit_sensitive)],
)
async def switch_facility(
    payload: SwitchFacilityRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _, session = await service.get_session_for_access_token(db, request.cookies.get(ACCESS_COOKIE_NAME) or "")
    tokens = await service.switch_facility(db, current_user, session, payload.facility_id)

    settings = get_settings()
    set_auth_cookies(
        response,
        settings=settings,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        access_max_age=settings.access_token_expire_minutes * 60,
        refresh_max_age=settings.refresh_token_expire_days * 86400,
    )
    set_committed_value(current_user, "facility_id", payload.facility_id)
    set_tenant_context(
        tenant_id=current_user.tenant_id, facility_id=payload.facility_id, actor_user_id=current_user.id
    )
    await audit_service.record_event(
        db,
        action="auth.facility_switched",
        resource_type="user_session",
        resource_id=session.id,
        after={"facility_id": str(payload.facility_id)},
    )
    tenant, facility = await _load_context(db, current_user)
    doctor_id = await _find_linked_doctor_id(db, current_user)
    body = MeResponse(
        user=UserOut.from_user(current_user, doctor_id=doctor_id),
        tenant=tenant,
        facility=facility,
        facilities=await service.list_user_facilities(db, current_user),
    )
    return success_response(
        body.model_dump(mode="json"), request_id=getattr(request.state, "request_id", None)
    )


@router.post(
    "/password-reset/request",
    response_model=ApiResponse,
    summary="Email a password-reset link (always answers the same, whether or not the account exists)",
    dependencies=[Depends(_limit_sensitive)],
)
async def request_password_reset(
    payload: PasswordResetRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    identifier = payload.identifier.strip()
    check_rate_limit(f"reset-target:{identifier.lower()}", limit=3, window_seconds=3600)

    user = (
        await db.execute(
            select(User).where(
                (User.username == identifier) | (func.lower(User.email) == identifier.lower())
            )
        )
    ).scalar_one_or_none()

    debug_token = None
    if user is not None and user.is_active:
        raw_token = await user_tokens.issue_token(db, user, user_tokens.PASSWORD_RESET)
        link = user_tokens.build_link(user_tokens.PASSWORD_RESET, raw_token)
        settings = get_settings()
        await mailer.send_email(
            to=user.email,
            subject="Reset your ForaCare HIS password",
            body=(
                f"Hello {user.full_name},\n\nUse this link to choose a new password. It is valid for "
                f"{settings.user_token_reset_minutes} minutes and can be used once:\n\n{link}\n\n"
                "If you did not request this, you can ignore this email."
            ),
        )
        await audit_service.record_event(
            db,
            action="auth.password_reset_requested",
            resource_type="user",
            resource_id=user.id,
            actor_user_id=user.id,
            actor_username=user.username,
            tenant_id=user.tenant_id,
            facility_id=user.facility_id,
        )
        if settings.is_local:
            debug_token = raw_token

    return success_response(
        PasswordResetRequestedResponse(debug_token=debug_token).model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


async def _set_password_with_token(
    purpose: str, audit_action: str, payload: SetPasswordWithTokenRequest, request: Request, db: AsyncSession
):
    user = await user_tokens.consume_token_and_set_password(
        db, payload.token, purpose, payload.new_password
    )
    await audit_service.record_event(
        db,
        action=audit_action,
        resource_type="user",
        resource_id=user.id,
        actor_user_id=user.id,
        actor_username=user.username,
        tenant_id=user.tenant_id,
        facility_id=user.facility_id,
    )
    return success_response({"changed": True}, request_id=getattr(request.state, "request_id", None))


@router.post(
    "/password-reset/confirm",
    response_model=ApiResponse,
    summary="Set a new password using an emailed reset token",
    dependencies=[Depends(_limit_sensitive)],
)
async def confirm_password_reset(
    payload: SetPasswordWithTokenRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    return await _set_password_with_token(
        user_tokens.PASSWORD_RESET, "auth.password_reset_completed", payload, request, db
    )


@router.post(
    "/activate",
    response_model=ApiResponse,
    summary="Activate an invited account by choosing a password",
    dependencies=[Depends(_limit_sensitive)],
)
async def activate_account(
    payload: SetPasswordWithTokenRequest, request: Request, db: AsyncSession = Depends(get_db)
):
    return await _set_password_with_token(
        user_tokens.ACTIVATION, "auth.account_activated", payload, request, db
    )
