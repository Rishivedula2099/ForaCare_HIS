import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.permissions import ensure_same_facility, ensure_same_tenant
from app.modules.audit import service as audit_service
from app.modules.auth.models import User
from app.modules.departments.models import Department
from app.modules.doctors.models import Doctor
from app.modules.doctors.schemas import DoctorCreateRequest, DoctorOut, DoctorUpdateRequest
from app.modules.facilities.models import Facility


async def _get_department_or_404(db: AsyncSession, department_id: uuid.UUID) -> Department:
    result = await db.execute(select(Department).where(Department.id == department_id))
    department = result.scalar_one_or_none()
    if department is None:
        raise NotFoundError("Department not found.")
    return department


async def _generate_doctor_code(db: AsyncSession, facility: Facility) -> str:
    result = await db.execute(
        select(func.count()).select_from(Doctor).where(Doctor.facility_id == facility.id)
    )
    sequence = (result.scalar_one() or 0) + 1
    return f"DR-{facility.facility_code}-{str(sequence).zfill(4)}"


async def list_doctors(
    db: AsyncSession,
    current_user: User,
    *,
    name: str | None = None,
    department_id: uuid.UUID | None = None,
) -> list[DoctorOut]:
    stmt = select(Doctor).where(
        Doctor.tenant_id == current_user.tenant_id,
        Doctor.facility_id == current_user.facility_id,
    )
    if name:
        pattern = f"%{name}%"
        stmt = stmt.where(
            (Doctor.full_name.ilike(pattern))
            | (Doctor.doctor_code.ilike(pattern))
            | (Doctor.specialization.ilike(pattern))
        )
    if department_id:
        stmt = stmt.where(Doctor.department_id == department_id)
    stmt = stmt.order_by(Doctor.full_name)

    result = await db.execute(stmt)
    return [DoctorOut.model_validate(doctor) for doctor in result.scalars().unique().all()]


async def _get_doctor_or_404(db: AsyncSession, doctor_id: uuid.UUID) -> Doctor:
    result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = result.scalar_one_or_none()
    if doctor is None:
        raise NotFoundError("Doctor not found.")
    return doctor


async def get_doctor(db: AsyncSession, doctor_id: uuid.UUID, current_user: User) -> DoctorOut:
    doctor = await _get_doctor_or_404(db, doctor_id)
    ensure_same_tenant(doctor.tenant_id, current_user)
    ensure_same_facility(doctor.facility_id, current_user)
    return DoctorOut.model_validate(doctor)


async def create_doctor(
    db: AsyncSession, payload: DoctorCreateRequest, current_user: User
) -> DoctorOut:
    department = await _get_department_or_404(db, payload.department_id)
    ensure_same_tenant(department.tenant_id, current_user)
    ensure_same_facility(department.facility_id, current_user)

    facility_result = await db.execute(
        select(Facility).where(Facility.id == current_user.facility_id)
    )
    facility = facility_result.scalar_one_or_none()
    if facility is None:
        raise NotFoundError("Facility not found.")

    doctor_code = await _generate_doctor_code(db, facility)

    doctor = Doctor(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        doctor_code=doctor_code,
        **payload.model_dump(),
    )
    db.add(doctor)
    await db.flush()

    await audit_service.record_event(
        db,
        action="doctors.created",
        resource_type="doctor",
        resource_id=doctor.id,
        after=DoctorOut.model_validate(doctor).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(doctor)

    return DoctorOut.model_validate(doctor)


async def update_doctor(
    db: AsyncSession, doctor_id: uuid.UUID, payload: DoctorUpdateRequest, current_user: User
) -> DoctorOut:
    doctor = await _get_doctor_or_404(db, doctor_id)
    ensure_same_tenant(doctor.tenant_id, current_user)
    ensure_same_facility(doctor.facility_id, current_user)

    if payload.department_id is not None and payload.department_id != doctor.department_id:
        department = await _get_department_or_404(db, payload.department_id)
        ensure_same_tenant(department.tenant_id, current_user)
        ensure_same_facility(department.facility_id, current_user)

    before = DoctorOut.model_validate(doctor).model_dump(mode="json")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(doctor, field, value)
    await db.flush()

    await audit_service.record_event(
        db,
        action="doctors.updated",
        resource_type="doctor",
        resource_id=doctor.id,
        before=before,
        after=DoctorOut.model_validate(doctor).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(doctor)

    return DoctorOut.model_validate(doctor)
