import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.audit import service as audit_service
from app.modules.rbac.models import Permission, Role
from app.modules.rbac.schemas import PermissionOut, RoleDetailOut, RoleSummaryOut


async def list_roles(db: AsyncSession) -> list[RoleSummaryOut]:
    result = await db.execute(select(Role).order_by(Role.name))
    roles = result.scalars().all()
    return [
        RoleSummaryOut(
            id=role.id,
            code=role.code,
            name=role.name,
            description=role.description,
            is_system=role.is_system,
            permission_count=len(role.permissions),
        )
        for role in roles
    ]


async def _get_role_or_404(db: AsyncSession, role_id: uuid.UUID) -> Role:
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if role is None:
        raise NotFoundError("Role not found.")
    return role


async def get_role(db: AsyncSession, role_id: uuid.UUID) -> RoleDetailOut:
    role = await _get_role_or_404(db, role_id)
    return RoleDetailOut(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        permissions=[PermissionOut.model_validate(p) for p in role.permissions],
    )


async def list_permissions(db: AsyncSession) -> list[PermissionOut]:
    result = await db.execute(select(Permission).order_by(Permission.module, Permission.code))
    return [PermissionOut.model_validate(p) for p in result.scalars().all()]


async def set_role_permissions(
    db: AsyncSession, role_id: uuid.UUID, permission_ids: list[uuid.UUID]
) -> RoleDetailOut:
    role = await _get_role_or_404(db, role_id)
    before_codes = sorted(permission.code for permission in role.permissions)

    result = await db.execute(select(Permission).where(Permission.id.in_(permission_ids)))
    permissions = result.scalars().all()
    if len(permissions) != len(set(permission_ids)):
        raise NotFoundError("One or more permission ids were not found.")

    role.permissions = permissions
    await db.flush()

    after_codes = sorted(permission.code for permission in role.permissions)
    await audit_service.record_event(
        db,
        action="rbac.role.permissions_updated",
        resource_type="role",
        resource_id=role.id,
        before={"permission_codes": before_codes},
        after={"permission_codes": after_codes},
        commit=False,
    )
    await db.commit()
    await db.refresh(role)

    return RoleDetailOut(
        id=role.id,
        code=role.code,
        name=role.name,
        description=role.description,
        is_system=role.is_system,
        permissions=[PermissionOut.model_validate(p) for p in role.permissions],
    )
