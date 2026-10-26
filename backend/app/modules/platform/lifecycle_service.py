"""P10-B02: platform-operator management of existing organisations."""
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.modules.audit import service as audit_service
from app.modules.auth import mailer, user_tokens
from app.modules.auth.models import User, UserFacilityMembership, UserToken
from app.modules.facilities.models import Facility
from app.modules.facilities.schemas import FacilityOut
from app.modules.lifecycle import service as lifecycle
from app.modules.platform.lifecycle_schemas import (
    AdministratorAssigned,
    AdministratorSummary,
    AssignAdministratorRequest,
    TenantDetail,
    TenantSummary,
    TenantUpdateRequest,
)
from app.modules.platform.schemas import FacilityInput
from app.modules.platform.service import _duplicate_error, find_duplicates
from app.modules.rbac.models import Role
from app.modules.tenants.models import Tenant


async def get_tenant_or_404(db: AsyncSession, tenant_id) -> Tenant:
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    if tenant is None:
        raise NotFoundError("Organisation not found.")
    return tenant


async def _summary(db: AsyncSession, tenant: Tenant) -> TenantSummary:
    total, active = (
        await db.execute(
            select(func.count(), func.count().filter(Facility.is_active.is_(True))).where(
                Facility.tenant_id == tenant.id
            )
        )
    ).one()
    users = (await db.execute(select(func.count()).select_from(User).where(User.tenant_id == tenant.id))).scalar_one()
    return TenantSummary(
        id=tenant.id,
        name=tenant.name,
        code=tenant.code,
        is_active=tenant.is_active,
        status_reason=tenant.status_reason,
        facility_count=total,
        active_facility_count=active,
        user_count=users,
    )


async def list_tenants(db: AsyncSession) -> list[TenantSummary]:
    tenants = (await db.execute(select(Tenant).order_by(Tenant.name))).scalars().all()
    return [await _summary(db, t) for t in tenants]


async def get_tenant_detail(db: AsyncSession, tenant_id) -> TenantDetail:
    tenant = await get_tenant_or_404(db, tenant_id)
    summary = await _summary(db, tenant)
    facilities = (
        await db.execute(select(Facility).where(Facility.tenant_id == tenant.id).order_by(Facility.name))
    ).scalars().all()
    admins = (
        await db.execute(
            select(User)
            .join(Role, Role.id == User.role_id)
            .where(User.tenant_id == tenant.id, Role.code == "HOSPITAL_ADMIN")
            .order_by(User.username)
        )
    ).scalars().all()
    pending = {
        row[0]
        for row in await db.execute(
            select(UserToken.user_id).where(
                UserToken.purpose == user_tokens.ACTIVATION, UserToken.used_at.is_(None)
            )
        )
    }
    return TenantDetail(
        **summary.model_dump(),
        facilities=[FacilityOut.model_validate(f).model_dump(mode="json") for f in facilities],
        administrators=[
            AdministratorSummary(
                id=a.id,
                username=a.username,
                email=a.email,
                full_name=a.full_name,
                is_active=a.is_active,
                pending_activation=a.id in pending and a.last_login_at is None,
            )
            for a in admins
        ],
    )


async def update_tenant(db: AsyncSession, tenant_id, payload: TenantUpdateRequest, operator: User) -> TenantSummary:
    tenant = await get_tenant_or_404(db, tenant_id)
    before = {"name": tenant.name}
    tenant.name = payload.name
    await audit_service.record_event(
        db,
        action="platform.tenant_updated",
        resource_type="tenant",
        resource_id=tenant.id,
        before=before,
        after={"name": tenant.name},
        tenant_id=tenant.id,
        commit=False,
    )
    await db.commit()
    return await _summary(db, tenant)


async def suspend_tenant(db: AsyncSession, tenant_id, reason: str, operator: User) -> TenantSummary:
    tenant = await get_tenant_or_404(db, tenant_id)
    await lifecycle.suspend_tenant(db, tenant, reason, operator)
    return await _summary(db, tenant)


async def reactivate_tenant(db: AsyncSession, tenant_id, operator: User) -> TenantSummary:
    tenant = await get_tenant_or_404(db, tenant_id)
    await lifecycle.reactivate_tenant(db, tenant, operator)
    return await _summary(db, tenant)


def _require_active(tenant: Tenant) -> None:
    if not tenant.is_active:
        raise ConflictError("This organisation is suspended. Reactivate it first.", code="TENANT_SUSPENDED")


async def create_facility_in_tenant(db: AsyncSession, tenant_id, fac: FacilityInput, operator: User) -> FacilityOut:
    tenant = await get_tenant_or_404(db, tenant_id)
    _require_active(tenant)
    if (await find_duplicates(db, facility_code=fac.facility_code)).get("facility.facility_code"):
        raise _duplicate_error(["facility.facility_code"])
    facility = Facility(
        tenant_id=tenant.id,
        name=fac.name,
        facility_code=fac.facility_code,
        facility_type=fac.facility_type,
        address=fac.composed_address(),
        phone=fac.phone,
        email=str(fac.email).lower(),
        timezone=fac.timezone,
        currency=fac.currency,
    )
    db.add(facility)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise _duplicate_error(["facility.facility_code"]) from None
    await audit_service.record_event(
        db,
        action="platform.facility_created",
        resource_type="facility",
        resource_id=facility.id,
        after={"facility_code": facility.facility_code, "facility_type": facility.facility_type},
        tenant_id=tenant.id,
        facility_id=facility.id,
        commit=False,
    )
    await db.commit()
    return FacilityOut.model_validate(facility)


async def set_facility_status(
    db: AsyncSession, tenant_id, facility_id, operator: User, *, active: bool, reason: str | None
) -> FacilityOut:
    """The facility must belong to the organisation named in the URL."""
    facility = (
        await db.execute(select(Facility).where(Facility.id == facility_id, Facility.tenant_id == tenant_id))
    ).scalar_one_or_none()
    if facility is None:
        raise NotFoundError("Facility not found in this organisation.")
    if active:
        await lifecycle.reactivate_facility(db, facility, operator)
    else:
        await lifecycle.deactivate_facility(db, facility, reason or "", operator, actor_facility_id=None)
    await db.refresh(facility)
    return FacilityOut.model_validate(facility)


async def assign_administrator(
    db: AsyncSession, tenant_id, payload: AssignAdministratorRequest, operator: User
) -> AdministratorAssigned:
    """Audited and privileged: adds a Hospital Admin to an existing organisation."""
    tenant = await get_tenant_or_404(db, tenant_id)
    _require_active(tenant)
    # A client-supplied facility id is only ever accepted after checking it belongs to this tenant.
    facility = (
        await db.execute(select(Facility).where(Facility.id == payload.facility_id, Facility.tenant_id == tenant.id))
    ).scalar_one_or_none()
    if facility is None:
        raise NotFoundError("Facility not found in this organisation.")
    if not facility.is_active:
        raise ConflictError("That facility is inactive.", code="FACILITY_INACTIVE")
    role = (await db.execute(select(Role).where(Role.code == "HOSPITAL_ADMIN"))).scalar_one()
    admin = payload.administrator
    taken = await find_duplicates(db, username=admin.username, email=str(admin.email))
    clashes = [field for field, is_taken in taken.items() if is_taken]
    if clashes:
        raise _duplicate_error(clashes)
    user = User(
        tenant_id=tenant.id,
        facility_id=facility.id,
        username=admin.username,
        email=str(admin.email).lower(),
        full_name=admin.full_name,
        role_id=role.id,
        password_hash=user_tokens.unusable_password_hash(),
        is_active=True,
    )
    try:
        db.add(user)
        await db.flush()
        db.add(UserFacilityMembership(user_id=user.id, facility_id=facility.id, is_default=True))
        token = await user_tokens.issue_token(db, user, user_tokens.ACTIVATION, commit=False)
        await audit_service.record_event(
            db,
            action="platform.administrator_assigned",
            resource_type="user",
            resource_id=user.id,
            after={"username": user.username, "role": "HOSPITAL_ADMIN", "facility_code": facility.facility_code},
            tenant_id=tenant.id,
            facility_id=facility.id,
            commit=False,
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise _duplicate_error(["administrator.username"]) from None
    link = user_tokens.build_link(user_tokens.ACTIVATION, token)
    emailed = False
    if payload.send_activation_email:
        emailed = await mailer.send_email(
            to=user.email,
            subject="Activate your ForaCare HIS account",
            body=f"Hello {user.full_name},\n\nYou are now an administrator of {tenant.name}. "
            f"Choose your password to activate your account:\n\n{link}\n",
        )
    return AdministratorAssigned(
        administrator_id=user.id,
        administrator_username=user.username,
        administrator_email=user.email,
        facility_id=facility.id,
        activation_link=link,
        activation_expires_hours=get_settings().user_token_activation_hours,
        activation_email_sent=emailed,
    )
