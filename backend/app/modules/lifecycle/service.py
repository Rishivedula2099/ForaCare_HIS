"""P10-B02: activation, suspension and safe deactivation of tenants (hospital
organisations) and facilities.

Hierarchy enforced here and in the callers:

    platform Super Admin -> tenant (organisation) -> facilities -> Hospital Admin -> staff

* Only the platform operator suspends / reactivates a tenant (never their own).
* A Hospital Admin may deactivate / reactivate facilities of their own tenant only,
  never the last active one, never the one they are working in, and never while
  patients are admitted or the OPD queue is open.
* Every change records who, when and why, revokes the sessions it invalidates,
  and writes an audit event.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.modules.audit import service as audit_service
from app.modules.auth.models import User, UserSession
from app.modules.facilities.models import Facility
from app.modules.ipd.models import Admission
from app.modules.opd.models import Token
from app.modules.tenants.models import Tenant

OPEN_QUEUE_STATUSES = ("WAITING", "CALLED", "IN_CONSULTATION", "SKIPPED")


async def revoke_sessions(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID | None = None,
    facility_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    except_session_id: uuid.UUID | None = None,
) -> int:
    """Ends every live session matching the filters; returns how many."""
    now = datetime.now(timezone.utc)
    stmt = update(UserSession).where(UserSession.revoked_at.is_(None))
    if user_id is not None:
        stmt = stmt.where(UserSession.user_id == user_id)
    if facility_id is not None:
        stmt = stmt.where(UserSession.facility_id == facility_id)
    if tenant_id is not None:
        stmt = stmt.where(UserSession.user_id.in_(select(User.id).where(User.tenant_id == tenant_id)))
    if except_session_id is not None:
        stmt = stmt.where(UserSession.id != except_session_id)
    result = await db.execute(stmt.values(revoked_at=now, status="revoked"))
    return result.rowcount or 0


def _stamp(entity: Tenant | Facility, *, active: bool, reason: str | None, actor: User) -> None:
    entity.is_active = active
    entity.status_reason = reason
    entity.status_changed_at = datetime.now(timezone.utc)
    entity.status_changed_by = actor.id


# ---------------------------------------------------------------------- tenants


async def suspend_tenant(db: AsyncSession, tenant: Tenant, reason: str, operator: User) -> Tenant:
    if tenant.id == operator.tenant_id:
        raise ConflictError(
            "You cannot suspend the organisation you are signed in to.", code="TENANT_SELF_SUSPEND"
        )
    if not tenant.is_active:
        raise ConflictError("This organisation is already suspended.", code="ALREADY_SUSPENDED")
    _stamp(tenant, active=False, reason=reason, actor=operator)
    revoked = await revoke_sessions(db, tenant_id=tenant.id)
    await audit_service.record_event(
        db,
        action="platform.tenant_suspended",
        resource_type="tenant",
        resource_id=tenant.id,
        after={"reason": reason, "sessions_revoked": revoked},
        tenant_id=tenant.id,
        commit=False,
    )
    await db.commit()
    return tenant


async def reactivate_tenant(db: AsyncSession, tenant: Tenant, operator: User) -> Tenant:
    if tenant.is_active:
        raise ConflictError("This organisation is already active.", code="ALREADY_ACTIVE")
    _stamp(tenant, active=True, reason=None, actor=operator)
    await audit_service.record_event(
        db,
        action="platform.tenant_reactivated",
        resource_type="tenant",
        resource_id=tenant.id,
        tenant_id=tenant.id,
        commit=False,
    )
    await db.commit()
    return tenant


# -------------------------------------------------------------------- facilities


async def _open_work(db: AsyncSession, facility: Facility) -> list[tuple[str, str]]:
    admitted = (
        await db.execute(
            select(func.count())
            .select_from(Admission)
            .where(Admission.facility_id == facility.id, Admission.status == "ADMITTED")
        )
    ).scalar_one()
    queued = (
        await db.execute(
            select(func.count())
            .select_from(Token)
            .where(Token.facility_id == facility.id, Token.status.in_(OPEN_QUEUE_STATUSES))
        )
    ).scalar_one()
    blocking: list[tuple[str, str]] = []
    if admitted:
        blocking.append(("admissions", f"{admitted} patient(s) are currently admitted. Discharge or transfer them first."))
    if queued:
        blocking.append(("opd_queue", f"{queued} OPD token(s) are still open. Complete or cancel them first."))
    return blocking


async def deactivate_facility(
    db: AsyncSession,
    facility: Facility,
    reason: str,
    actor: User,
    *,
    actor_facility_id: uuid.UUID | None,
) -> Facility:
    """`actor_facility_id` is the facility the actor is currently working in
    (None for the platform operator, who works outside the tenant)."""
    if not facility.is_active:
        raise ConflictError("This facility is already inactive.", code="ALREADY_INACTIVE")
    if actor_facility_id is not None and actor_facility_id == facility.id:
        raise ConflictError(
            "You are working in this facility. Switch to another facility before deactivating it.",
            code="FACILITY_IN_USE",
        )
    other_active = (
        await db.execute(
            select(func.count())
            .select_from(Facility)
            .where(Facility.tenant_id == facility.tenant_id, Facility.is_active.is_(True), Facility.id != facility.id)
        )
    ).scalar_one()
    if other_active == 0:
        raise ConflictError(
            "This is the organisation's last active facility. Suspend the organisation instead.",
            code="LAST_ACTIVE_FACILITY",
        )
    blocking = await _open_work(db, facility)
    if blocking:
        raise ConflictError(
            "This facility still has open clinical work.", code="FACILITY_HAS_OPEN_WORK", details=blocking
        )

    _stamp(facility, active=False, reason=reason, actor=actor)
    revoked = await revoke_sessions(db, facility_id=facility.id)
    await audit_service.record_event(
        db,
        action="facilities.deactivated",
        resource_type="facility",
        resource_id=facility.id,
        after={"reason": reason, "sessions_revoked": revoked},
        tenant_id=facility.tenant_id,
        facility_id=facility.id,
        commit=False,
    )
    await db.commit()
    return facility


async def reactivate_facility(db: AsyncSession, facility: Facility, actor: User) -> Facility:
    if facility.is_active:
        raise ConflictError("This facility is already active.", code="ALREADY_ACTIVE")
    tenant = (await db.execute(select(Tenant).where(Tenant.id == facility.tenant_id))).scalar_one()
    if not tenant.is_active:
        raise ConflictError("The organisation is suspended; reactivate it first.", code="TENANT_SUSPENDED")
    _stamp(facility, active=True, reason=None, actor=actor)
    await audit_service.record_event(
        db,
        action="facilities.reactivated",
        resource_type="facility",
        resource_id=facility.id,
        tenant_id=facility.tenant_id,
        facility_id=facility.id,
        commit=False,
    )
    await db.commit()
    return facility
