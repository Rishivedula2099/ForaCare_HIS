"""P10-B02: staff management, bounded by the organisation hierarchy.

    platform Super Admin -> organisation -> facilities -> Hospital Admin -> staff

A caller here is always acting inside THEIR OWN organisation. Rules enforced:

* a user is only ever found by id within the caller's tenant (404 otherwise);
* platform operators (SUPER_ADMIN) are invisible to, and unmanageable by, anyone else;
* only "tenant-assignable" roles can be handed out - never SUPER_ADMIN, never a role
  holding a platform permission - so a Hospital Admin cannot mint a Super Admin;
* every client-supplied facility id must be an active facility of the caller's tenant;
* nobody changes their own role, facilities or active state (no self-escalation or
  self-lockout), and the organisation's last active Hospital Admin cannot be removed.
"""
import uuid

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.modules.audit import service as audit_service
from app.modules.auth import mailer, user_tokens
from app.modules.auth.models import User, UserFacilityMembership, UserToken
from app.modules.facilities.models import Facility
from app.modules.lifecycle.service import revoke_sessions
from app.modules.rbac.models import Role
from app.modules.rbac.service import PLATFORM_ONLY_PERMISSIONS, PLATFORM_OPERATOR_ROLE
from app.modules.users.schemas import (
    FacilityRef,
    RoleRef,
    UserAdminOut,
    UserCreateRequest,
    UserInvited,
    UserUpdateRequest,
)

HOSPITAL_ADMIN = "HOSPITAL_ADMIN"


def is_assignable(role: Role) -> bool:
    return role.code != PLATFORM_OPERATOR_ROLE and not ({p.code for p in role.permissions} & PLATFORM_ONLY_PERMISSIONS)


async def assignable_roles(db: AsyncSession) -> list[Role]:
    roles = (await db.execute(select(Role).order_by(Role.name))).scalars().all()
    return [r for r in roles if is_assignable(r)]


async def _load_user(db: AsyncSession, user_id: uuid.UUID, caller: User) -> User:
    """Tenant-scoped lookup. Another tenant's user, and a platform operator seen by
    a non-operator, are indistinguishable from a user that does not exist."""
    user = (
        await db.execute(select(User).where(User.id == user_id, User.tenant_id == caller.tenant_id))
    ).scalar_one_or_none()
    if user is None or (user.role.code == PLATFORM_OPERATOR_ROLE and caller.role.code != PLATFORM_OPERATOR_ROLE):
        raise NotFoundError("User not found.")
    return user


async def _facility_refs(db: AsyncSession, user: User) -> list[FacilityRef]:
    rows = (
        await db.execute(
            select(Facility, UserFacilityMembership.is_default)
            .join(UserFacilityMembership, UserFacilityMembership.facility_id == Facility.id)
            .where(UserFacilityMembership.user_id == user.id, Facility.tenant_id == user.tenant_id)
            .order_by(UserFacilityMembership.is_default.desc(), Facility.name)
        )
    ).all()
    return [
        FacilityRef(id=f.id, name=f.name, facility_code=f.facility_code, is_active=f.is_active, is_default=d)
        for f, d in rows
    ]


async def _to_out(db: AsyncSession, user: User) -> UserAdminOut:
    return UserAdminOut(
        id=user.id,
        username=user.username,
        email=user.email,
        phone=user.phone,
        full_name=user.full_name,
        role=RoleRef(id=user.role.id, code=user.role.code, name=user.role.name),
        is_active=user.is_active,
        facilities=await _facility_refs(db, user),
        last_login_at=user.last_login_at,
        pending_activation=user.last_login_at is None,
    )


async def list_users(
    db: AsyncSession, caller: User, *, facility_id: uuid.UUID | None = None, include_inactive: bool = True
) -> list[UserAdminOut]:
    stmt = select(User).where(User.tenant_id == caller.tenant_id)
    if facility_id is not None:
        await _tenant_facilities(db, caller, [facility_id], require_active=False)  # ownership check
        stmt = stmt.where(
            User.id.in_(select(UserFacilityMembership.user_id).where(UserFacilityMembership.facility_id == facility_id))
        )
    if not include_inactive:
        stmt = stmt.where(User.is_active.is_(True))
    users = (await db.execute(stmt.order_by(User.full_name))).scalars().all()
    if caller.role.code != PLATFORM_OPERATOR_ROLE:
        users = [u for u in users if u.role.code != PLATFORM_OPERATOR_ROLE]
    return [await _to_out(db, u) for u in users]


async def get_user(db: AsyncSession, user_id: uuid.UUID, caller: User) -> UserAdminOut:
    return await _to_out(db, await _load_user(db, user_id, caller))


async def _tenant_facilities(
    db: AsyncSession, caller: User, ids: list[uuid.UUID], *, require_active: bool = True
) -> list[Facility]:
    """Never trust a client-supplied facility id: each must belong to the caller's
    tenant (and be active when it is being granted)."""
    unique = list(dict.fromkeys(ids))
    found = (
        await db.execute(select(Facility).where(Facility.id.in_(unique), Facility.tenant_id == caller.tenant_id))
    ).scalars().all()
    by_id = {f.id: f for f in found}
    missing = [i for i in unique if i not in by_id]
    if missing:
        raise NotFoundError("Facility not found.")
    if require_active:
        inactive = [f for f in found if not f.is_active]
        if inactive:
            raise ConflictError(
                "Inactive facilities cannot be assigned.",
                code="FACILITY_INACTIVE",
                details=[("facility_ids", f"{f.name} is inactive.") for f in inactive],
            )
    return [by_id[i] for i in unique]


async def _assignable_role(db: AsyncSession, role_id: uuid.UUID) -> Role:
    role = (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none()
    if role is None:
        raise NotFoundError("Role not found.")
    if not is_assignable(role):
        raise ForbiddenError("That role cannot be assigned by a hospital administrator.", code="ROLE_NOT_ASSIGNABLE")
    return role


async def _other_active_admins(db: AsyncSession, caller: User, excluding: uuid.UUID) -> int:
    return (
        await db.execute(
            select(func.count())
            .select_from(User)
            .join(Role, Role.id == User.role_id)
            .where(
                User.tenant_id == caller.tenant_id,
                User.is_active.is_(True),
                Role.code == HOSPITAL_ADMIN,
                User.id != excluding,
            )
        )
    ).scalar_one()


async def _guard_last_admin(db: AsyncSession, caller: User, target: User) -> None:
    if target.role.code == HOSPITAL_ADMIN and target.is_active and await _other_active_admins(db, caller, target.id) == 0:
        raise ConflictError(
            "This is the organisation's last active Hospital Admin.", code="LAST_ADMIN"
        )


async def _set_memberships(
    db: AsyncSession, user: User, facilities: list[Facility], default_id: uuid.UUID | None
) -> None:
    wanted = {f.id for f in facilities}
    if default_id is not None and default_id not in wanted:
        raise ConflictError("The default facility must be one of the assigned facilities.", code="VALIDATION_ERROR")
    existing = {
        m.facility_id: m
        for m in (
            await db.execute(select(UserFacilityMembership).where(UserFacilityMembership.user_id == user.id))
        ).scalars()
    }
    for facility_id, membership in existing.items():
        if facility_id not in wanted:
            await db.delete(membership)
    for facility_id in wanted - set(existing):
        db.add(UserFacilityMembership(user_id=user.id, facility_id=facility_id, is_default=False))
    await db.flush()
    current_default = next((fid for fid, m in existing.items() if m.is_default and fid in wanted), None)
    chosen = default_id or current_default or facilities[0].id
    rows = (await db.execute(select(UserFacilityMembership).where(UserFacilityMembership.user_id == user.id))).scalars()
    for membership in rows:
        membership.is_default = membership.facility_id == chosen
    user.facility_id = chosen  # home facility mirrors the default membership


async def invite_user(db: AsyncSession, payload: UserCreateRequest, caller: User) -> UserInvited:
    role = await _assignable_role(db, payload.role_id)
    facilities = await _tenant_facilities(db, caller, payload.facility_ids)
    default_id = payload.default_facility_id or facilities[0].id
    if default_id not in {f.id for f in facilities}:
        raise ConflictError("The default facility must be one of the assigned facilities.", code="VALIDATION_ERROR")

    email = str(payload.email).lower()
    clashes = []
    if (await db.execute(select(User.id).where(User.username == payload.username))).first():
        clashes.append(("username", "This username is already taken."))
    if (await db.execute(select(User.id).where(func.lower(User.email) == email))).first():
        clashes.append(("email", "An account with this email address already exists."))
    if clashes:
        raise ConflictError("Some of these details are already in use.", code="DUPLICATE", details=clashes)

    user = User(
        tenant_id=caller.tenant_id,
        facility_id=default_id,
        username=payload.username,
        email=email,
        full_name=payload.full_name,
        role_id=role.id,
        password_hash=user_tokens.unusable_password_hash(),
        is_active=True,
    )
    try:
        db.add(user)
        await db.flush()
        for facility in facilities:
            db.add(UserFacilityMembership(user_id=user.id, facility_id=facility.id, is_default=facility.id == default_id))
        token = await user_tokens.issue_token(db, user, user_tokens.ACTIVATION, commit=False)
        await audit_service.record_event(
            db,
            action="users.invited",
            resource_type="user",
            resource_id=user.id,
            after={
                "username": user.username,
                "role": role.code,
                "facility_codes": sorted(f.facility_code for f in facilities),
            },
            commit=False,
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ConflictError("Some of these details are already in use.", code="DUPLICATE") from None
    await db.refresh(user)
    link = user_tokens.build_link(user_tokens.ACTIVATION, token)
    emailed = False
    if payload.send_activation_email:
        emailed = await mailer.send_email(
            to=user.email,
            subject="Activate your ForaCare HIS account",
            body=f"Hello {user.full_name},\n\nAn account was created for you. Choose your password:\n\n{link}\n",
        )
    return UserInvited(
        user=await _to_out(db, user),
        activation_link=link,
        activation_expires_hours=get_settings().user_token_activation_hours,
        activation_email_sent=emailed,
    )


async def update_user(db: AsyncSession, user_id: uuid.UUID, payload: UserUpdateRequest, caller: User) -> UserAdminOut:
    target = await _load_user(db, user_id, caller)
    before = await _to_out(db, target)
    changes = payload.model_dump(exclude_unset=True)
    is_self = target.id == caller.id

    if payload.full_name is not None:
        target.full_name = payload.full_name
    if "phone" in changes:
        target.phone = payload.phone or None

    if payload.role_id is not None and payload.role_id != target.role_id:
        if is_self:
            raise ForbiddenError("You cannot change your own role.", code="SELF_MODIFICATION")
        if target.role.code == PLATFORM_OPERATOR_ROLE:
            raise ForbiddenError("A platform operator's role cannot be changed here.", code="ROLE_NOT_ASSIGNABLE")
        role = await _assignable_role(db, payload.role_id)
        if role.code != HOSPITAL_ADMIN:
            await _guard_last_admin(db, caller, target)
        target.role_id = role.id
        await db.flush()
        await db.refresh(target)

    if payload.facility_ids is not None:
        if is_self:
            raise ForbiddenError("You cannot change your own facility access.", code="SELF_MODIFICATION")
        facilities = await _tenant_facilities(db, caller, payload.facility_ids)
        await _set_memberships(db, target, facilities, payload.default_facility_id)
    elif payload.default_facility_id is not None:
        current = await _facility_refs(db, target)
        await _set_memberships(
            db,
            target,
            await _tenant_facilities(db, caller, [f.id for f in current], require_active=False),
            payload.default_facility_id,
        )

    await db.flush()
    await db.refresh(target)
    after = await _to_out(db, target)
    await audit_service.record_event(
        db,
        action="users.updated",
        resource_type="user",
        resource_id=target.id,
        before={"role": before.role.code, "facilities": sorted(f.facility_code for f in before.facilities), "full_name": before.full_name},
        after={"role": after.role.code, "facilities": sorted(f.facility_code for f in after.facilities), "full_name": after.full_name},
        commit=False,
    )
    await db.commit()
    return await _to_out(db, target)


async def set_active(db: AsyncSession, user_id: uuid.UUID, caller: User, *, active: bool) -> UserAdminOut:
    target = await _load_user(db, user_id, caller)
    if target.id == caller.id:
        raise ForbiddenError("You cannot change your own active state.", code="SELF_MODIFICATION")
    if target.role.code == PLATFORM_OPERATOR_ROLE:
        raise ForbiddenError("A platform operator cannot be changed here.", code="ROLE_NOT_ASSIGNABLE")
    if target.is_active == active:
        raise ConflictError(
            "This user is already active." if active else "This user is already deactivated.", code="NO_CHANGE"
        )
    if not active:
        await _guard_last_admin(db, caller, target)
    target.is_active = active
    revoked = 0
    if not active:
        revoked = await revoke_sessions(db, user_id=target.id)
    await audit_service.record_event(
        db,
        action="users.reactivated" if active else "users.deactivated",
        resource_type="user",
        resource_id=target.id,
        after={"username": target.username, "sessions_revoked": revoked},
        commit=False,
    )
    await db.commit()
    return await _to_out(db, target)


async def resend_activation(db: AsyncSession, user_id: uuid.UUID, caller: User, *, send_email: bool) -> UserInvited:
    target = await _load_user(db, user_id, caller)
    if target.last_login_at is not None:
        raise ConflictError("This user has already signed in; use password reset instead.", code="ALREADY_ACTIVATED")
    if not target.is_active:
        raise ConflictError("This user is deactivated.", code="USER_INACTIVE")
    token = await user_tokens.issue_token(db, target, user_tokens.ACTIVATION)
    link = user_tokens.build_link(user_tokens.ACTIVATION, token)
    emailed = False
    if send_email:
        emailed = await mailer.send_email(
            to=target.email,
            subject="Activate your ForaCare HIS account",
            body=f"Hello {target.full_name},\n\nChoose your password to activate your account:\n\n{link}\n",
        )
    await audit_service.record_event(
        db, action="users.activation_resent", resource_type="user", resource_id=target.id
    )
    return UserInvited(
        user=await _to_out(db, target),
        activation_link=link,
        activation_expires_hours=get_settings().user_token_activation_hours,
        activation_email_sent=emailed,
    )
