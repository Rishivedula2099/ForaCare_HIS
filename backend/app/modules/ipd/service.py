import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.permissions import ensure_same_facility, ensure_same_tenant
from app.modules.audit import service as audit_service
from app.modules.auth.models import User
from app.modules.ipd.models import (
    BED_STATUS_CODES,
    Admission,
    Bed,
    BedAssignment,
    Consent,
    Discharge,
    Room,
    Transfer,
    Ward,
)
from app.modules.ipd.schemas import (
    AdmissionCreateRequest,
    AdmissionOut,
    BedCreateRequest,
    BedOut,
    BedUpdateRequest,
    ConsentCreateRequest,
    ConsentOut,
    CurrentOccupant,
    DischargeCreateRequest,
    DischargeOut,
    PatientSummary,
    RoomCreateRequest,
    RoomOut,
    RoomUpdateRequest,
    TransferCreateRequest,
    TransferOut,
    WardCreateRequest,
    WardOut,
    WardUpdateRequest,
)
from app.modules.patients.models import Patient

# The bed state machine (P4-B02). Every manual status change goes through
# `update_bed`, which is the only place that may write `Bed.status` from a
# user-supplied value - so this map is a complete description of what's
# reachable from where. OCCUPIED has no manual transitions in either
# direction: a bed only becomes OCCUPIED via `create_admission`/
# `create_transfer`, and only leaves it via `create_transfer`/
# `create_discharge` (which move it to CLEANING, not through this map).
BED_TRANSITIONS: dict[str, set[str]] = {
    "AVAILABLE": {"RESERVED", "MAINTENANCE", "BLOCKED"},
    "RESERVED": {"AVAILABLE", "BLOCKED"},
    "OCCUPIED": set(),
    "CLEANING": {"AVAILABLE", "MAINTENANCE", "BLOCKED"},
    "MAINTENANCE": {"AVAILABLE", "BLOCKED"},
    "BLOCKED": {"AVAILABLE", "MAINTENANCE"},
}
_ALLOCATABLE_BED_STATUSES = {"AVAILABLE", "RESERVED"}

# ---------------------------------------------------------------------------
# Ward
# ---------------------------------------------------------------------------


async def list_wards(db: AsyncSession, current_user: User) -> list[WardOut]:
    stmt = (
        select(Ward)
        .where(Ward.tenant_id == current_user.tenant_id, Ward.facility_id == current_user.facility_id)
        .order_by(Ward.name)
    )
    result = await db.execute(stmt)
    return [WardOut.model_validate(ward) for ward in result.scalars().all()]


async def _get_ward_or_404(db: AsyncSession, ward_id: uuid.UUID) -> Ward:
    result = await db.execute(select(Ward).where(Ward.id == ward_id))
    ward = result.scalar_one_or_none()
    if ward is None:
        raise NotFoundError("Ward not found.")
    return ward


async def create_ward(db: AsyncSession, payload: WardCreateRequest, current_user: User) -> WardOut:
    existing = await db.execute(
        select(Ward).where(Ward.facility_id == current_user.facility_id, Ward.code == payload.code)
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A ward with this code already exists in this facility.")

    ward = Ward(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        **payload.model_dump(),
    )
    db.add(ward)
    await db.flush()

    await audit_service.record_event(
        db,
        action="ipd.ward_created",
        resource_type="ipd_ward",
        resource_id=ward.id,
        after=WardOut.model_validate(ward).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(ward)
    return WardOut.model_validate(ward)


async def update_ward(
    db: AsyncSession, ward_id: uuid.UUID, payload: WardUpdateRequest, current_user: User
) -> WardOut:
    ward = await _get_ward_or_404(db, ward_id)
    ensure_same_tenant(ward.tenant_id, current_user)
    ensure_same_facility(ward.facility_id, current_user)

    before = WardOut.model_validate(ward).model_dump(mode="json")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ward, field, value)
    await db.flush()

    await audit_service.record_event(
        db,
        action="ipd.ward_updated",
        resource_type="ipd_ward",
        resource_id=ward.id,
        before=before,
        after=WardOut.model_validate(ward).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(ward)
    return WardOut.model_validate(ward)


# ---------------------------------------------------------------------------
# Room
# ---------------------------------------------------------------------------


async def list_rooms(
    db: AsyncSession, current_user: User, *, ward_id: uuid.UUID | None = None
) -> list[RoomOut]:
    stmt = select(Room).where(
        Room.tenant_id == current_user.tenant_id, Room.facility_id == current_user.facility_id
    )
    if ward_id:
        stmt = stmt.where(Room.ward_id == ward_id)
    stmt = stmt.order_by(Room.room_number)

    result = await db.execute(stmt)
    return [RoomOut.model_validate(room) for room in result.scalars().all()]


async def _get_room_or_404(db: AsyncSession, room_id: uuid.UUID) -> Room:
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if room is None:
        raise NotFoundError("Room not found.")
    return room


async def create_room(db: AsyncSession, payload: RoomCreateRequest, current_user: User) -> RoomOut:
    ward = await _get_ward_or_404(db, payload.ward_id)
    ensure_same_tenant(ward.tenant_id, current_user)
    ensure_same_facility(ward.facility_id, current_user)

    existing = await db.execute(
        select(Room).where(Room.ward_id == payload.ward_id, Room.room_number == payload.room_number)
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A room with this number already exists in this ward.")

    room = Room(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        **payload.model_dump(),
    )
    db.add(room)
    await db.flush()

    await audit_service.record_event(
        db,
        action="ipd.room_created",
        resource_type="ipd_room",
        resource_id=room.id,
        after=RoomOut.model_validate(room).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(room)
    return RoomOut.model_validate(room)


async def update_room(
    db: AsyncSession, room_id: uuid.UUID, payload: RoomUpdateRequest, current_user: User
) -> RoomOut:
    room = await _get_room_or_404(db, room_id)
    ensure_same_tenant(room.tenant_id, current_user)
    ensure_same_facility(room.facility_id, current_user)

    before = RoomOut.model_validate(room).model_dump(mode="json")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(room, field, value)
    await db.flush()

    await audit_service.record_event(
        db,
        action="ipd.room_updated",
        resource_type="ipd_room",
        resource_id=room.id,
        before=before,
        after=RoomOut.model_validate(room).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(room)
    return RoomOut.model_validate(room)


# ---------------------------------------------------------------------------
# Bed
# ---------------------------------------------------------------------------


async def _current_occupants_by_bed_id(
    db: AsyncSession, bed_ids: list[uuid.UUID]
) -> dict[uuid.UUID, CurrentOccupant]:
    if not bed_ids:
        return {}

    stmt = (
        select(BedAssignment, Admission, Patient)
        .join(Admission, Admission.id == BedAssignment.admission_id)
        .join(Patient, Patient.id == Admission.patient_id)
        .where(BedAssignment.bed_id.in_(bed_ids), BedAssignment.status == "ACTIVE")
    )
    result = await db.execute(stmt)

    occupants: dict[uuid.UUID, CurrentOccupant] = {}
    for assignment, admission, patient in result.all():
        occupants[assignment.bed_id] = CurrentOccupant(
            admission_id=admission.id,
            admission_number=admission.admission_number,
            admitted_at=admission.admitted_at,
            patient=PatientSummary(
                id=patient.id,
                uid=patient.uid,
                mrn=patient.mrn,
                first_name=patient.first_name,
                middle_name=patient.middle_name,
                last_name=patient.last_name,
                gender=patient.gender,
                dob=str(patient.dob),
            ),
        )
    return occupants


def _serialize_bed(bed: Bed, occupant: CurrentOccupant | None) -> BedOut:
    return BedOut(
        id=bed.id,
        tenant_id=bed.tenant_id,
        facility_id=bed.facility_id,
        ward_id=bed.ward_id,
        room_id=bed.room_id,
        bed_number=bed.bed_number,
        status=bed.status,
        is_active=bed.is_active,
        created_at=bed.created_at,
        updated_at=bed.updated_at,
        ward=WardOut.model_validate(bed.ward),
        room=RoomOut.model_validate(bed.room),
        current_occupant=occupant,
    )


async def list_beds(
    db: AsyncSession,
    current_user: User,
    *,
    ward_id: uuid.UUID | None = None,
    room_id: uuid.UUID | None = None,
    status: str | None = None,
) -> list[BedOut]:
    stmt = select(Bed).where(
        Bed.tenant_id == current_user.tenant_id, Bed.facility_id == current_user.facility_id
    )
    if ward_id:
        stmt = stmt.where(Bed.ward_id == ward_id)
    if room_id:
        stmt = stmt.where(Bed.room_id == room_id)
    if status:
        # An unrecognized status value matches no beds rather than raising -
        # mirrors the pre-P4-B02 behavior of filtering on the raw string.
        stmt = stmt.where(Bed.status_code == BED_STATUS_CODES.get(status, -1))
    stmt = stmt.order_by(Bed.bed_number)

    result = await db.execute(stmt)
    beds = list(result.scalars().all())
    occupants = await _current_occupants_by_bed_id(db, [bed.id for bed in beds])
    return [_serialize_bed(bed, occupants.get(bed.id)) for bed in beds]


async def _get_bed_or_404(db: AsyncSession, bed_id: uuid.UUID) -> Bed:
    result = await db.execute(select(Bed).where(Bed.id == bed_id))
    bed = result.scalar_one_or_none()
    if bed is None:
        raise NotFoundError("Bed not found.")
    return bed


async def get_bed(db: AsyncSession, bed_id: uuid.UUID, current_user: User) -> BedOut:
    bed = await _get_bed_or_404(db, bed_id)
    ensure_same_tenant(bed.tenant_id, current_user)
    ensure_same_facility(bed.facility_id, current_user)
    occupants = await _current_occupants_by_bed_id(db, [bed.id])
    return _serialize_bed(bed, occupants.get(bed.id))


async def create_bed(db: AsyncSession, payload: BedCreateRequest, current_user: User) -> BedOut:
    room = await _get_room_or_404(db, payload.room_id)
    ensure_same_tenant(room.tenant_id, current_user)
    ensure_same_facility(room.facility_id, current_user)
    if room.ward_id != payload.ward_id:
        raise ConflictError("Room does not belong to the given ward.")

    existing = await db.execute(
        select(Bed).where(Bed.room_id == payload.room_id, Bed.bed_number == payload.bed_number)
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A bed with this number already exists in this room.")

    bed = Bed(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        **payload.model_dump(),
    )
    db.add(bed)
    await db.flush()

    await audit_service.record_event(
        db,
        action="ipd.bed_created",
        resource_type="ipd_bed",
        resource_id=bed.id,
        commit=False,
    )
    await db.commit()
    await db.refresh(bed)
    return await get_bed(db, bed.id, current_user)


async def update_bed(
    db: AsyncSession, bed_id: uuid.UUID, payload: BedUpdateRequest, current_user: User
) -> BedOut:
    bed = await _get_bed_or_404(db, bed_id)
    ensure_same_tenant(bed.tenant_id, current_user)
    ensure_same_facility(bed.facility_id, current_user)

    current_status = bed.status
    if payload.status is not None and payload.status != current_status:
        if payload.status not in BED_TRANSITIONS.get(current_status, set()):
            raise AppError(
                f"Cannot move a bed from {current_status} to {payload.status}.", code="INVALID_TRANSITION"
            )
        bed.status = payload.status

    for field, value in payload.model_dump(exclude_unset=True, exclude={"status"}).items():
        setattr(bed, field, value)
    await db.flush()

    await audit_service.record_event(
        db,
        action="ipd.bed_updated",
        resource_type="ipd_bed",
        resource_id=bed.id,
        commit=False,
    )
    await db.commit()
    await db.refresh(bed)
    return await get_bed(db, bed.id, current_user)


# ---------------------------------------------------------------------------
# Admission
# ---------------------------------------------------------------------------


async def _generate_admission_number(db: AsyncSession, current_user: User) -> str:
    year = datetime.now(timezone.utc).strftime("%Y")
    result = await db.execute(
        select(Admission).where(Admission.tenant_id == current_user.tenant_id)
    )
    count = len(result.scalars().all())
    return f"ADM-{year}-{count + 1:06d}"


async def list_admissions(
    db: AsyncSession,
    current_user: User,
    *,
    patient_id: uuid.UUID | None = None,
    status: str | None = None,
) -> list[AdmissionOut]:
    stmt = select(Admission).where(
        Admission.tenant_id == current_user.tenant_id, Admission.facility_id == current_user.facility_id
    )
    if patient_id:
        stmt = stmt.where(Admission.patient_id == patient_id)
    if status:
        stmt = stmt.where(Admission.status == status)
    stmt = stmt.order_by(Admission.admitted_at.desc())

    result = await db.execute(stmt)
    return [AdmissionOut.model_validate(admission) for admission in result.scalars().all()]


async def _get_admission_or_404(db: AsyncSession, admission_id: uuid.UUID) -> Admission:
    result = await db.execute(select(Admission).where(Admission.id == admission_id))
    admission = result.scalar_one_or_none()
    if admission is None:
        raise NotFoundError("Admission not found.")
    return admission


async def get_admission(db: AsyncSession, admission_id: uuid.UUID, current_user: User) -> AdmissionOut:
    admission = await _get_admission_or_404(db, admission_id)
    ensure_same_tenant(admission.tenant_id, current_user)
    ensure_same_facility(admission.facility_id, current_user)
    return AdmissionOut.model_validate(admission)


def _active_assignment(admission: Admission) -> BedAssignment | None:
    for assignment in admission.bed_assignments:
        if assignment.status == "ACTIVE":
            return assignment
    return None


async def create_admission(
    db: AsyncSession, payload: AdmissionCreateRequest, current_user: User
) -> AdmissionOut:
    bed = await _get_bed_or_404(db, payload.bed_id)
    ensure_same_tenant(bed.tenant_id, current_user)
    ensure_same_facility(bed.facility_id, current_user)

    if bed.status not in _ALLOCATABLE_BED_STATUSES:
        raise ConflictError("This bed is not available for admission.")

    existing_admission = await db.execute(
        select(Admission).where(
            Admission.tenant_id == current_user.tenant_id,
            Admission.patient_id == payload.patient_id,
            Admission.status == "ADMITTED",
        )
    )
    if existing_admission.scalar_one_or_none() is not None:
        raise ConflictError("This patient already has an active admission.")

    admission = Admission(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        patient_id=payload.patient_id,
        admitting_doctor_id=payload.admitting_doctor_id,
        department_id=payload.department_id,
        admission_type=payload.admission_type,
        notes=payload.notes,
        admission_number=await _generate_admission_number(db, current_user),
        admitted_by=current_user.id,
    )
    db.add(admission)
    await db.flush()

    assignment = BedAssignment(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        admission_id=admission.id,
        bed_id=bed.id,
        assigned_by=current_user.id,
    )
    db.add(assignment)
    bed.status = "OCCUPIED"
    await db.flush()

    await audit_service.record_event(
        db,
        action="ipd.admission_created",
        resource_type="ipd_admission",
        resource_id=admission.id,
        commit=False,
    )
    await db.commit()
    await db.refresh(admission)
    return AdmissionOut.model_validate(admission)


# ---------------------------------------------------------------------------
# Transfer
# ---------------------------------------------------------------------------


async def create_transfer(
    db: AsyncSession, admission_id: uuid.UUID, payload: TransferCreateRequest, current_user: User
) -> TransferOut:
    admission = await _get_admission_or_404(db, admission_id)
    ensure_same_tenant(admission.tenant_id, current_user)
    ensure_same_facility(admission.facility_id, current_user)

    if admission.status != "ADMITTED":
        raise ConflictError("Only an active admission can be transferred.")

    current_assignment = _active_assignment(admission)
    if current_assignment is None:
        raise ConflictError("This admission has no active bed assignment.")

    to_bed = await _get_bed_or_404(db, payload.to_bed_id)
    ensure_same_tenant(to_bed.tenant_id, current_user)
    ensure_same_facility(to_bed.facility_id, current_user)
    if to_bed.status not in _ALLOCATABLE_BED_STATUSES:
        raise ConflictError("The target bed is not available.")

    from_bed = await _get_bed_or_404(db, current_assignment.bed_id)

    current_assignment.status = "RELEASED"
    current_assignment.released_at = datetime.now(timezone.utc)
    # A vacated bed needs cleaning before it can be reused, same as a
    # discharge (see create_discharge below) - not returned straight to
    # AVAILABLE.
    from_bed.status = "CLEANING"

    new_assignment = BedAssignment(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        admission_id=admission.id,
        bed_id=to_bed.id,
        assigned_by=current_user.id,
    )
    db.add(new_assignment)
    to_bed.status = "OCCUPIED"

    transfer = Transfer(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        admission_id=admission.id,
        from_bed_id=from_bed.id,
        to_bed_id=to_bed.id,
        reason=payload.reason,
        transferred_by=current_user.id,
    )
    db.add(transfer)
    await db.flush()

    await audit_service.record_event(
        db,
        action="ipd.transfer_created",
        resource_type="ipd_admission",
        resource_id=admission.id,
        commit=False,
    )
    await db.commit()
    await db.refresh(transfer)
    return TransferOut.model_validate(transfer)


# ---------------------------------------------------------------------------
# Discharge
# ---------------------------------------------------------------------------


async def create_discharge(
    db: AsyncSession, admission_id: uuid.UUID, payload: DischargeCreateRequest, current_user: User
) -> DischargeOut:
    admission = await _get_admission_or_404(db, admission_id)
    ensure_same_tenant(admission.tenant_id, current_user)
    ensure_same_facility(admission.facility_id, current_user)

    if admission.status != "ADMITTED":
        raise ConflictError("This admission is not currently active.")

    current_assignment = _active_assignment(admission)
    if current_assignment is not None:
        bed = await _get_bed_or_404(db, current_assignment.bed_id)
        current_assignment.status = "RELEASED"
        current_assignment.released_at = datetime.now(timezone.utc)
        bed.status = "CLEANING"

    admission.status = "DISCHARGED"

    discharge = Discharge(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        admission_id=admission.id,
        discharged_by=current_user.id,
        **payload.model_dump(),
    )
    db.add(discharge)
    await db.flush()

    await audit_service.record_event(
        db,
        action="ipd.discharge_created",
        resource_type="ipd_admission",
        resource_id=admission.id,
        commit=False,
    )
    await db.commit()
    await db.refresh(discharge)
    return DischargeOut.model_validate(discharge)


# ---------------------------------------------------------------------------
# Consent
# ---------------------------------------------------------------------------


async def list_consents(db: AsyncSession, admission_id: uuid.UUID, current_user: User) -> list[ConsentOut]:
    admission = await _get_admission_or_404(db, admission_id)
    ensure_same_tenant(admission.tenant_id, current_user)
    ensure_same_facility(admission.facility_id, current_user)

    result = await db.execute(
        select(Consent).where(Consent.admission_id == admission_id).order_by(Consent.recorded_at)
    )
    return [ConsentOut.model_validate(consent) for consent in result.scalars().all()]


async def create_consent(
    db: AsyncSession, admission_id: uuid.UUID, payload: ConsentCreateRequest, current_user: User
) -> ConsentOut:
    admission = await _get_admission_or_404(db, admission_id)
    ensure_same_tenant(admission.tenant_id, current_user)
    ensure_same_facility(admission.facility_id, current_user)

    consent = Consent(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        admission_id=admission.id,
        recorded_by=current_user.id,
        **payload.model_dump(),
    )
    db.add(consent)
    await db.flush()

    await audit_service.record_event(
        db,
        action="ipd.consent_recorded",
        resource_type="ipd_admission",
        resource_id=admission.id,
        commit=False,
    )
    await db.commit()
    await db.refresh(consent)
    return ConsentOut.model_validate(consent)
