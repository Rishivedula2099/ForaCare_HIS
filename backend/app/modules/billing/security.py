"""Billing-specific permission dependency (S5-B01 / P5-B06).

Wraps `app.core.permissions.require_permissions` so a denied attempt at a
financial operation is recorded as an audit event before the 403 is
raised, not just rejected silently. Scoped to billing rather than changing
the shared `require_permissions` dependency every other module also uses,
since only billing asked for this.
"""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import ForbiddenError
from app.core.permissions import get_current_user
from app.modules.audit import service as audit_service
from app.modules.auth.models import User


def require_billing_permission(*permission_codes: str):
    async def _dependency(
        request: Request,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> User:
        user_permission_codes = {permission.code for permission in current_user.role.permissions}
        if not set(permission_codes).issubset(user_permission_codes):
            await audit_service.record_event(
                db,
                action="billing.access_denied",
                resource_type="billing_permission",
                resource_id=None,
                after={
                    "required_permissions": list(permission_codes),
                    "path": request.url.path,
                    "method": request.method,
                },
                actor_user_id=current_user.id,
                commit=True,
            )
            raise ForbiddenError("You do not have permission to perform this action.")
        return current_user

    return _dependency
