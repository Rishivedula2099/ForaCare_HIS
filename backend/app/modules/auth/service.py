import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.core.security import create_token, decode_token, hash_password, hash_token_jti, verify_password
from app.modules.auth.models import User, UserSession
from app.modules.otp import service as otp_service


@dataclass
class IssuedTokens:
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime
    token_type: str = "bearer"


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid username or password.")

    if not user.is_active:
        raise UnauthorizedError("This account is inactive. Contact your administrator.")

    return user


async def issue_tokens(
    db: AsyncSession, user: User, *, ip_address: str | None, user_agent: str | None
) -> IssuedTokens:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    session_id = str(uuid.uuid4())

    access_token, _, access_expires_at = create_token(
        token_type="access",
        sub=str(user.id),
        sid=session_id,
        tenant_id=str(user.tenant_id),
        facility_id=str(user.facility_id),
        role=user.role.code,
    )
    refresh_token, refresh_jti, refresh_expires_at = create_token(
        token_type="refresh",
        sub=str(user.id),
        sid=session_id,
        tenant_id=str(user.tenant_id),
        facility_id=str(user.facility_id),
        role=user.role.code,
    )

    session = UserSession(
        id=uuid.UUID(session_id),
        user_id=user.id,
        facility_id=user.facility_id,
        refresh_token_jti_hash=hash_token_jti(refresh_jti),
        family_id=uuid.UUID(session_id),
        created_at=now,
        last_used_at=now,
        expires_at=refresh_expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
        status="active",
    )
    db.add(session)
    user.last_login_at = now
    await db.commit()

    return IssuedTokens(
        access_token=access_token,
        refresh_token=refresh_token,
        access_expires_at=access_expires_at,
        refresh_expires_at=refresh_expires_at,
    )


async def _load_active_session(db: AsyncSession, session_id: uuid.UUID) -> UserSession | None:
    result = await db.execute(select(UserSession).where(UserSession.id == session_id))
    return result.scalar_one_or_none()


async def get_session_for_access_token(db: AsyncSession, access_token: str) -> tuple[dict, UserSession]:
    try:
        claims = decode_token(access_token, expected_type="access")
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Access token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid access token.") from exc

    try:
        session_id = uuid.UUID(claims["sid"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Invalid access token.") from exc

    session = await _load_active_session(db, session_id)
    now = datetime.now(timezone.utc)
    if (
        session is None
        or session.revoked_at is not None
        or session.status != "active"
        or session.expires_at < now
    ):
        raise UnauthorizedError("Session has been revoked or has expired.")

    return claims, session


async def rotate_session(
    db: AsyncSession, raw_refresh_token: str, *, ip_address: str | None, user_agent: str | None
) -> IssuedTokens:
    from app.modules.audit import service as audit_service

    try:
        claims = decode_token(raw_refresh_token, expected_type="refresh")
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Refresh token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid refresh token.") from exc

    try:
        session_id = uuid.UUID(claims["sid"])
        user_id = uuid.UUID(claims["sub"])
        presented_jti = claims["jti"]
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Invalid refresh token.") from exc

    session = await _load_active_session(db, session_id)
    now = datetime.now(timezone.utc)

    if session is None or session.user_id != user_id:
        raise UnauthorizedError("Refresh token is invalid or has been revoked.")

    if session.revoked_at is not None or session.status != "active" or session.expires_at < now:
        raise UnauthorizedError("Refresh token is invalid or has been revoked.")

    if session.refresh_token_jti_hash != hash_token_jti(presented_jti):
        # A refresh token was replayed after its lineage already rotated
        # past it - treat this as token theft and kill the whole session.
        session.revoked_at = now
        session.status = "reused"
        await db.commit()
        await audit_service.record_event(
            db,
            action="auth.security.refresh_reuse_detected",
            resource_type="user_session",
            resource_id=session.id,
            actor_user_id=user_id,
        )
        raise UnauthorizedError("Refresh token reuse detected. Please sign in again.")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise UnauthorizedError("Account is no longer active.")

    settings = get_settings()
    new_access_token, _, access_expires_at = create_token(
        token_type="access",
        sub=str(user.id),
        sid=str(session.id),
        tenant_id=str(user.tenant_id),
        facility_id=str(user.facility_id),
        role=user.role.code,
    )
    new_refresh_token, new_refresh_jti, _ = create_token(
        token_type="refresh",
        sub=str(user.id),
        sid=str(session.id),
        tenant_id=str(user.tenant_id),
        facility_id=str(user.facility_id),
        role=user.role.code,
    )

    session.refresh_token_jti_hash = hash_token_jti(new_refresh_jti)
    session.last_used_at = now
    session.ip_address = ip_address or session.ip_address
    session.user_agent = user_agent or session.user_agent
    await db.commit()

    return IssuedTokens(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        access_expires_at=access_expires_at,
        refresh_expires_at=session.expires_at,
    )


async def revoke_session_by_id(db: AsyncSession, session_id: uuid.UUID) -> UserSession | None:
    session = await _load_active_session(db, session_id)
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)
        session.status = "revoked"
        await db.commit()
    return session


async def revoke_all_sessions_for_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(UserSession).where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
    )
    for session in result.scalars().all():
        session.revoked_at = now
        session.status = "revoked"
    await db.commit()


async def change_password(db: AsyncSession, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise UnauthorizedError("Current password is incorrect.")

    user.password_hash = hash_password(new_password)
    await db.commit()


async def request_email_change(db: AsyncSession, user: User, new_email: str) -> str | None:
    existing = await db.execute(select(User).where(User.email == new_email, User.id != user.id))
    if existing.scalar_one_or_none() is not None:
        from app.core.exceptions import ConflictError

        raise ConflictError("That email address is already in use.")

    _, raw_code = await otp_service.request_otp(
        db, user_id=user.id, purpose="email_change", target_value=new_email
    )
    settings = get_settings()
    return raw_code if settings.is_local else None


async def verify_email_change(db: AsyncSession, user: User, new_email: str, code: str) -> None:
    await otp_service.verify_otp(
        db, user_id=user.id, purpose="email_change", target_value=new_email, code=code
    )
    user.email = new_email
    user.email_verified_at = datetime.now(timezone.utc)
    await db.commit()


async def request_phone_change(db: AsyncSession, user: User, new_phone: str) -> str | None:
    existing = await db.execute(select(User).where(User.phone == new_phone, User.id != user.id))
    if existing.scalar_one_or_none() is not None:
        from app.core.exceptions import ConflictError

        raise ConflictError("That phone number is already in use.")

    _, raw_code = await otp_service.request_otp(
        db, user_id=user.id, purpose="phone_change", target_value=new_phone
    )
    settings = get_settings()
    return raw_code if settings.is_local else None


async def verify_phone_change(db: AsyncSession, user: User, new_phone: str, code: str) -> None:
    await otp_service.verify_otp(
        db, user_id=user.id, purpose="phone_change", target_value=new_phone, code=code
    )
    user.phone = new_phone
    user.phone_verified_at = datetime.now(timezone.utc)
    await db.commit()
