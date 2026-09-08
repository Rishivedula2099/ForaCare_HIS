import uuid

import jwt
from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.context import set_tenant_context
from app.core.database import get_db
from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import decode_access_token
from app.modules.auth.models import User
from app.modules.rbac.models import Role


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

    result = await db.execute(
        select(User)
        .options(selectinload(User.role).selectinload(Role.permissions))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise UnauthorizedError("Account is no longer active.")

    set_tenant_context(tenant_id=user.tenant_id, facility_id=user.facility_id, actor_user_id=user.id)

    return user


def require_roles(*role_codes: str):
    async def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.code not in role_codes:
            raise ForbiddenError("You do not have permission to perform this action.")
        return current_user

    return _dependency


def require_permissions(*permission_codes: str):
    async def _dependency(current_user: User = Depends(get_current_user)) -> User:
        user_permission_codes = {permission.code for permission in current_user.role.permissions}
        if not set(permission_codes).issubset(user_permission_codes):
            raise ForbiddenError("You do not have permission to perform this action.")
        return current_user

    return _dependency


def ensure_same_tenant(resource_tenant_id: uuid.UUID, current_user: User) -> None:
    """Raises if a resource belongs to a tenant other than the caller's.

    A `NotFoundError` (not `ForbiddenError`) is used deliberately: confirming
    that a resource exists in another tenant is itself a cross-tenant data
    leak, so a caller outside the tenant should see the same 404 they'd get
    for a resource that simply doesn't exist.
    """
    if resource_tenant_id != current_user.tenant_id:
        raise NotFoundError("Resource not found.")


def ensure_same_facility(resource_facility_id: uuid.UUID, current_user: User) -> None:
    """Raises if a facility-scoped resource belongs to another facility."""
    if resource_facility_id != current_user.facility_id:
        raise NotFoundError("Resource not found.")
