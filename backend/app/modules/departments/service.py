import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import ensure_same_facility, ensure_same_tenant
from app.modules.audit import service as audit_service
from app.modules.auth.models import User
from app.modules.departments.models import Department
from app.modules.departments.schemas import (
    DepartmentCreateRequest,
    DepartmentOut,
    DepartmentUpdateRequest,
)


async def list_departments(
    db: AsyncSession, current_user: User, *, name: str | None = None
) -> list[DepartmentOut]:
    stmt = select(Department).where(
        Department.tenant_id == current_user.tenant_id,
        Department.facility_id == current_user.facility_id,
    )
    if name:
        stmt = stmt.where(Department.name.ilike(f"%{name}%"))
    stmt = stmt.order_by(Department.name)

    result = await db.execute(stmt)
    return [DepartmentOut.model_validate(department) for department in result.scalars().all()]


async def _get_department_or_404(db: AsyncSession, department_id: uuid.UUID) -> Department:
    result = await db.execute(select(Department).where(Department.id == department_id))
    department = result.scalar_one_or_none()
    if department is None:
        raise NotFoundError("Department not found.")
    return department


async def get_department(
    db: AsyncSession, department_id: uuid.UUID, current_user: User
) -> DepartmentOut:
    department = await _get_department_or_404(db, department_id)
    ensure_same_tenant(department.tenant_id, current_user)
    ensure_same_facility(department.facility_id, current_user)
    return DepartmentOut.model_validate(department)


async def create_department(
    db: AsyncSession, payload: DepartmentCreateRequest, current_user: User
) -> DepartmentOut:
    existing = await db.execute(
        select(Department).where(
            Department.facility_id == current_user.facility_id,
            Department.code == payload.code,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A department with this code already exists in this facility.")

    department = Department(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        **payload.model_dump(),
    )
    db.add(department)
    await db.flush()

    await audit_service.record_event(
        db,
        action="departments.created",
        resource_type="department",
        resource_id=department.id,
        after=DepartmentOut.model_validate(department).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(department)

    return DepartmentOut.model_validate(department)


async def update_department(
    db: AsyncSession,
    department_id: uuid.UUID,
    payload: DepartmentUpdateRequest,
    current_user: User,
) -> DepartmentOut:
    department = await _get_department_or_404(db, department_id)
    ensure_same_tenant(department.tenant_id, current_user)
    ensure_same_facility(department.facility_id, current_user)

    before = DepartmentOut.model_validate(department).model_dump(mode="json")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(department, field, value)
    await db.flush()

    await audit_service.record_event(
        db,
        action="departments.updated",
        resource_type="department",
        resource_id=department.id,
        before=before,
        after=DepartmentOut.model_validate(department).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(department)

    return DepartmentOut.model_validate(department)
