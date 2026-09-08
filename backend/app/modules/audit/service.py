import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import (
    get_current_actor_user_id,
    get_current_facility_id,
    get_current_tenant_id,
    get_request_id,
)
from app.modules.audit.models import AuditLog
from app.modules.audit.schemas import AuditLogOut


async def record_event(
    db: AsyncSession,
    *,
    action: str,
    resource_type: str,
    resource_id: str | uuid.UUID | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    actor_user_id: uuid.UUID | None = None,
    actor_username: str | None = None,
    tenant_id: uuid.UUID | None = None,
    facility_id: uuid.UUID | None = None,
    commit: bool = True,
) -> AuditLog:
    """Writes one append-only audit event.

    Any identity/context field left unset falls back to the current
    request's context (populated by `get_current_user`), so a call site
    that already has the acting user in hand (e.g. mid-login, before that
    context is set) can pass it explicitly, while everything downstream of
    authentication can just call this with the fields specific to the
    event.
    """
    entry = AuditLog(
        request_id=get_request_id(),
        tenant_id=tenant_id if tenant_id is not None else get_current_tenant_id(),
        facility_id=facility_id if facility_id is not None else get_current_facility_id(),
        actor_user_id=actor_user_id if actor_user_id is not None else get_current_actor_user_id(),
        actor_username=actor_username,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        before=before,
        after=after,
    )
    db.add(entry)

    if commit:
        await db.commit()
    else:
        await db.flush()

    return entry


async def list_audit_logs(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    resource_type: str | None = None,
    actor_user_id: uuid.UUID | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[AuditLogOut]:
    stmt = select(AuditLog).where(AuditLog.tenant_id == tenant_id)

    if resource_type is not None:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
    if actor_user_id is not None:
        stmt = stmt.where(AuditLog.actor_user_id == actor_user_id)

    stmt = stmt.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(stmt)
    return [AuditLogOut.model_validate(row) for row in result.scalars().all()]
