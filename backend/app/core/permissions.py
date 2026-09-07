import uuid

import jwt
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.modules.auth.models import User, UserRole


def _extract_bearer_token(request: Request) -> str:
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing or malformed Authorization header.")
    return authorization.split(" ", 1)[1].strip()


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    token = _extract_bearer_token(request)

    try:
        claims = decode_access_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Access token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid access token.") from exc

    try:
        user_id = uuid.UUID(claims["sub"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Invalid access token.") from exc

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise UnauthorizedError("Account is no longer active.")

    return user


def require_roles(*roles: UserRole):
    async def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise ForbiddenError("You do not have permission to perform this action.")
        return current_user

    return _dependency
