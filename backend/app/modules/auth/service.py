import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.modules.auth.models import RefreshToken, User
from app.modules.auth.schemas import TokenResponse


# TODO(temporary): sign-in is bypassed for local development so any
# email/username + any password succeeds. Remove this block (and go back to
# `if user is None or not verify_password(...)`) before enabling real auth.
_DEV_BYPASS_FALLBACK_USERNAME = "dr.priya"


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User:
    settings = get_settings()
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if settings.is_local:
        if user is None:
            # Unknown username - fall back to a seeded demo user so login
            # still returns a valid tenant/facility/role context.
            fallback = await db.execute(
                select(User).where(User.username == _DEV_BYPASS_FALLBACK_USERNAME)
            )
            user = fallback.scalar_one_or_none()
    elif user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid username or password.")

    if user is None:
        raise UnauthorizedError("Invalid username or password.")

    if not user.is_active:
        raise UnauthorizedError("This account is inactive. Contact your administrator.")

    return user


def _access_token_claims(user: User) -> dict:
    return {
        "sub": str(user.id),
        "jti": str(uuid.uuid4()),
        "tenant_id": str(user.tenant_id),
        "facility_id": str(user.facility_id),
        "role": user.role.code,
    }


async def issue_tokens(db: AsyncSession, user: User) -> TokenResponse:
    settings = get_settings()

    access_token = create_access_token(_access_token_claims(user))

    raw_refresh_token = generate_refresh_token()
    refresh_expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh_token),
            expires_at=refresh_expires_at,
        )
    )
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def _get_valid_refresh_token(db: AsyncSession, raw_refresh_token: str) -> RefreshToken:
    token_hash = hash_refresh_token(raw_refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    token = result.scalar_one_or_none()

    if token is None or token.revoked_at is not None:
        raise UnauthorizedError("Refresh token is invalid or has been revoked.")

    if token.expires_at < datetime.now(timezone.utc):
        raise UnauthorizedError("Refresh token has expired.")

    return token


async def rotate_refresh_token(db: AsyncSession, raw_refresh_token: str) -> TokenResponse:
    token = await _get_valid_refresh_token(db, raw_refresh_token)

    result = await db.execute(select(User).where(User.id == token.user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise UnauthorizedError("Account is no longer active.")

    token.revoked_at = datetime.now(timezone.utc)
    await db.flush()

    return await issue_tokens(db, user)


async def revoke_refresh_token(db: AsyncSession, raw_refresh_token: str) -> RefreshToken | None:
    token_hash = hash_refresh_token(raw_refresh_token)
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    token = result.scalar_one_or_none()

    if token is not None and token.revoked_at is None:
        token.revoked_at = datetime.now(timezone.utc)
        await db.commit()

    return token


async def change_password(db: AsyncSession, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise UnauthorizedError("Current password is incorrect.")

    user.password_hash = hash_password(new_password)
    await db.commit()
