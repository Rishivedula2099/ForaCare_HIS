"""P10-B01: single-use account activation / password-reset tokens.

The raw token is 256 bits from `secrets`, shown only inside the link sent to
the user; the database keeps its SHA-256, so a database leak cannot be turned
into working links. Issuing a new token of a purpose invalidates earlier
unused ones, and consuming a token (or changing the password by any route)
ends every session of the user.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError
from app.core.security import hash_password
from app.modules.auth.models import User, UserSession, UserToken

ACTIVATION = "activation"
PASSWORD_RESET = "password_reset"

INVALID_TOKEN_ERROR = "This link is invalid or has expired. Request a new one."


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def unusable_password_hash() -> str:
    """A bcrypt hash of a random value nobody knows: an invited user cannot
    sign in until they set a password through their activation link."""
    return hash_password(secrets.token_urlsafe(48)[:60])


async def issue_token(db: AsyncSession, user: User, purpose: str) -> str:
    """Creates a fresh token (invalidating older unused ones); returns the raw value."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    lifetime = (
        timedelta(hours=settings.user_token_activation_hours)
        if purpose == ACTIVATION
        else timedelta(minutes=settings.user_token_reset_minutes)
    )
    await db.execute(
        update(UserToken)
        .where(UserToken.user_id == user.id, UserToken.purpose == purpose, UserToken.used_at.is_(None))
        .values(used_at=now)
    )
    raw = secrets.token_urlsafe(32)
    db.add(UserToken(user_id=user.id, purpose=purpose, token_hash=_hash(raw), expires_at=now + lifetime))
    await db.commit()
    return raw


def build_link(purpose: str, raw_token: str) -> str:
    settings = get_settings()
    base = (settings.frontend_base_url or settings.public_base_url or "http://localhost:3000").rstrip("/")
    path = "/activate-account" if purpose == ACTIVATION else "/reset-password"
    return f"{base}{path}?token={quote(raw_token)}"


async def consume_token_and_set_password(
    db: AsyncSession, raw_token: str, purpose: str, new_password: str
) -> User:
    """Validates the token, sets the new password, retires the token and
    revokes every session. One generic error for unknown/used/expired."""
    now = datetime.now(timezone.utc)
    token = (
        await db.execute(
            select(UserToken).where(UserToken.token_hash == _hash(raw_token)).with_for_update()
        )
    ).scalar_one_or_none()
    if (
        token is None
        or token.purpose != purpose
        or token.used_at is not None
        or token.expires_at < now
    ):
        raise UnauthorizedError(INVALID_TOKEN_ERROR, code="INVALID_TOKEN")

    user = (await db.execute(select(User).where(User.id == token.user_id))).scalar_one()
    if not user.is_active:
        raise UnauthorizedError(INVALID_TOKEN_ERROR, code="INVALID_TOKEN")

    token.used_at = now
    user.password_hash = hash_password(new_password)
    if purpose == ACTIVATION and user.email_verified_at is None:
        # The link went to the user's mailbox, so following it proves the address.
        user.email_verified_at = now
    for session in (
        await db.execute(
            select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        )
    ).scalars():
        session.revoked_at = now
        session.status = "revoked"
    await db.commit()
    return user
