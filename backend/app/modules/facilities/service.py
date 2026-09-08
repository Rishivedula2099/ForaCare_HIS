import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import ensure_same_tenant
from app.modules.audit import service as audit_service
from app.modules.auth.models import User
from app.modules.facilities.models import Facility
from app.modules.facilities.schemas import FacilityCreateRequest, FacilityOut, FacilityUpdateRequest


async def list_facilities(db: AsyncSession, current_user: User) -> list[FacilityOut]:
    result = await db.execute(
        select(Facility).where(Facility.tenant_id == current_user.tenant_id).order_by(Facility.name)
    )
    return [FacilityOut.model_validate(facility) for facility in result.scalars().all()]


async def _get_facility_or_404(db: AsyncSession, facility_id: uuid.UUID) -> Facility:
    result = await db.execute(select(Facility).where(Facility.id == facility_id))
    facility = result.scalar_one_or_none()
    if facility is None:
        raise NotFoundError("Facility not found.")
    return facility


async def get_facility(db: AsyncSession, facility_id: uuid.UUID, current_user: User) -> FacilityOut:
    facility = await _get_facility_or_404(db, facility_id)
    ensure_same_tenant(facility.tenant_id, current_user)
    return FacilityOut.model_validate(facility)


async def create_facility(
    db: AsyncSession, payload: FacilityCreateRequest, current_user: User
) -> FacilityOut:
    existing = await db.execute(
        select(Facility).where(Facility.facility_code == payload.facility_code)
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A facility with this code already exists.")

    facility = Facility(tenant_id=current_user.tenant_id, **payload.model_dump())
    db.add(facility)
    await db.flush()

    await audit_service.record_event(
        db,
        action="facilities.created",
        resource_type="facility",
        resource_id=facility.id,
        after=FacilityOut.model_validate(facility).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(facility)

    return FacilityOut.model_validate(facility)


async def update_facility(
    db: AsyncSession, facility_id: uuid.UUID, payload: FacilityUpdateRequest, current_user: User
) -> FacilityOut:
    facility = await _get_facility_or_404(db, facility_id)
    ensure_same_tenant(facility.tenant_id, current_user)

    before = FacilityOut.model_validate(facility).model_dump(mode="json")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(facility, field, value)
    await db.flush()

    await audit_service.record_event(
        db,
        action="facilities.updated",
        resource_type="facility",
        resource_id=facility.id,
        before=before,
        after=FacilityOut.model_validate(facility).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(facility)

    return FacilityOut.model_validate(facility)
