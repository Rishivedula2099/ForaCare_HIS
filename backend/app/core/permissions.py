import logging
import uuid

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.context import set_tenant_context
from app.core.cookies import ACCESS_COOKIE_NAME
from app.core.database import get_db
from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.modules.audit import service as audit_service
from app.modules.auth import service as auth_service
from app.modules.auth.models import User
from app.modules.rbac.models import Role


logger = logging.getLogger(__name__)


async def authenticate_by_access_token(access_token: str | None, db: AsyncSession) -> User:
    """Resolves the access-token cookie value into a `User` with role and
    permissions eager-loaded. Shared by the HTTP dependency below and by the
    WebSocket queue endpoint (app/api/v1/opd.py), which can't use a normal
    FastAPI `Depends(get_current_user)` chain since it reads the cookie off
    `WebSocket.cookies` rather than `Request.cookies`."""
    if not access_token:
        raise UnauthorizedError("Not authenticated.")

    claims, _session = await auth_service.get_session_for_access_token(db, access_token)

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


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    return await authenticate_by_access_token(request.cookies.get(ACCESS_COOKIE_NAME), db)


async def _audit_denial(db: AsyncSession, request: Request, user: User, required: list[str]) -> None:
    """P9-B03: a refused privileged call is a security event, not just a 403."""
    await audit_service.record_event(
        db,
        action="security.permission_denied",
        resource_type="endpoint",
        after={"method": request.method, "path": request.url.path, "required": required},
        actor_username=user.username,
    )


def require_roles(*role_codes: str):
    async def _dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if current_user.role.code not in role_codes:
            await _audit_denial(db, request, current_user, list(role_codes))
            raise ForbiddenError("You do not have permission to perform this action.")
        return current_user

    return _dependency


def require_permissions(*permission_codes: str):
    async def _dependency(
        request: Request,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        user_permission_codes = {permission.code for permission in current_user.role.permissions}
        if not set(permission_codes).issubset(user_permission_codes):
            await _audit_denial(db, request, current_user, list(permission_codes))
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
        logger.warning(
            "security.cross_tenant_access user=%s tenant=%s", current_user.id, current_user.tenant_id
        )
        raise NotFoundError("Resource not found.")


def ensure_same_facility(resource_facility_id: uuid.UUID, current_user: User) -> None:
    """Raises if a facility-scoped resource belongs to another facility."""
    if resource_facility_id != current_user.facility_id:
        logger.warning(
            "security.cross_facility_access user=%s facility=%s", current_user.id, current_user.facility_id
        )
        raise NotFoundError("Resource not found.")
