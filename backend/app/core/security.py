import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import bcrypt
import jwt

from app.core.config import get_settings

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _secret_for(token_type: TokenType) -> str:
    settings = get_settings()
    return settings.jwt_access_secret_key if token_type == "access" else settings.jwt_refresh_secret_key


def create_token(
    *,
    token_type: TokenType,
    sub: str,
    sid: str,
    tenant_id: str,
    facility_id: str,
    role: str,
    jti: str | None = None,
) -> tuple[str, str, datetime]:
    """Encodes an access or refresh JWT. Returns (token, jti, expires_at)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    lifetime = (
        timedelta(minutes=settings.access_token_expire_minutes)
        if token_type == "access"
        else timedelta(days=settings.refresh_token_expire_days)
    )
    expires_at = now + lifetime
    token_jti = jti or str(uuid.uuid4())

    payload = {
        "sub": sub,
        "sid": sid,
        "jti": token_jti,
        "type": token_type,
        "tenant_id": tenant_id,
        "facility_id": facility_id,
        "role": role,
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, _secret_for(token_type), algorithm=settings.jwt_algorithm)
    return token, token_jti, expires_at


def decode_token(token: str, *, expected_type: TokenType) -> dict[str, Any]:
    settings = get_settings()
    claims = jwt.decode(token, _secret_for(expected_type), algorithms=[settings.jwt_algorithm])
    if claims.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"Expected a {expected_type} token.")
    return claims


def hash_token_jti(jti: str) -> str:
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()
