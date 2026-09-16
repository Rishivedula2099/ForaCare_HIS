import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.modules.otp.models import OtpChallenge

RESEND_COOLDOWN_ERROR = "Please wait before requesting another code."
INVALID_OR_EXPIRED_ERROR = "Code is invalid or has expired."
TOO_MANY_ATTEMPTS_ERROR = "Too many incorrect attempts. Request a new code."


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


async def request_otp(
    db: AsyncSession, *, user_id, purpose: str, target_value: str
) -> tuple[OtpChallenge, str]:
    """Creates a fresh OTP challenge, enforcing the resend cooldown.

    Returns (challenge, raw_code). The raw code must never be logged; the
    caller is responsible for delivering it out-of-band (email/SMS) - it is
    only ever persisted as a hash.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(OtpChallenge)
        .where(
            OtpChallenge.user_id == user_id,
            OtpChallenge.purpose == purpose,
            OtpChallenge.target_value == target_value,
            OtpChallenge.consumed_at.is_(None),
        )
        .order_by(OtpChallenge.created_at.desc())
        .limit(1)
    )
    last_challenge = result.scalar_one_or_none()
    if last_challenge is not None:
        cooldown_until = last_challenge.created_at + timedelta(
            seconds=settings.otp_resend_cooldown_seconds
        )
        if now < cooldown_until:
            raise ConflictError(RESEND_COOLDOWN_ERROR, code="OTP_RESEND_COOLDOWN")
        # Superseded by the new challenge below; never let two live codes exist at once.
        last_challenge.consumed_at = now

    raw_code = _generate_code()
    challenge = OtpChallenge(
        user_id=user_id,
        purpose=purpose,
        target_value=target_value,
        code_hash=_hash_code(raw_code),
        max_attempts=settings.otp_max_attempts,
        expires_at=now + timedelta(minutes=settings.otp_expire_minutes),
    )
    db.add(challenge)
    await db.commit()
    await db.refresh(challenge)

    return challenge, raw_code


async def verify_otp(db: AsyncSession, *, user_id, purpose: str, target_value: str, code: str) -> None:
    """Raises UnauthorizedError on any invalid/expired/exhausted code; consumes on success."""
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(OtpChallenge)
        .where(
            OtpChallenge.user_id == user_id,
            OtpChallenge.purpose == purpose,
            OtpChallenge.target_value == target_value,
            OtpChallenge.consumed_at.is_(None),
        )
        .order_by(OtpChallenge.created_at.desc())
        .limit(1)
    )
    challenge = result.scalar_one_or_none()

    if challenge is None or challenge.expires_at < now:
        raise UnauthorizedError(INVALID_OR_EXPIRED_ERROR, code="OTP_INVALID")

    if challenge.attempts >= challenge.max_attempts:
        challenge.consumed_at = now
        await db.commit()
        raise UnauthorizedError(TOO_MANY_ATTEMPTS_ERROR, code="OTP_LOCKED")

    if _hash_code(code) != challenge.code_hash:
        challenge.attempts += 1
        await db.commit()
        raise UnauthorizedError(INVALID_OR_EXPIRED_ERROR, code="OTP_INVALID")

    challenge.consumed_at = now
    await db.commit()
