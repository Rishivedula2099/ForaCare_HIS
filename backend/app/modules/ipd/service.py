import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
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
    Deposit,
    Discharge,
    Room,
    Transfer,
    Ward,
)
from app.modules.ipd.schemas import (
    AdmissionCreateRequest,
    AdmissionOut,
    AdmissionUpdateRequest,
    BedCreateRequest,
    BedOut,
    BedUpdateRequest,
    ConsentCreateRequest,
    ConsentOut,
    CurrentOccupant,
    DepositCreateRequest,
    DepositOut,
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


async def _lock_patient_admission_slot(db: AsyncSession, patient_id: uuid.UUID) -> None:
    """Serializes admission creation for one patient (P4-B03) so two
    concurrent admit requests can't both pass the "no active admission"
    check before either commits. A `SELECT ... FOR UPDATE` can't cover this
    because a patient with no active admission has no existing `Admission`
    row to lock - mirrors `_lock_doctor_queue` in
    app/modules/opd/service.py. Always acquired before any bed row lock in
    the same transaction (see `create_admission`) so lock order stays
    consistent and can't deadlock against it."""
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"ipd-admission:{patient_id}"}
    )


async def _lock_admission_number_sequence(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Serializes admission-number generation for one tenant (P4-B03).

    `_generate_admission_number` counts existing rows and formats the next
    number - it has no row to `SELECT ... FOR UPDATE` until that row exists,
    so two concurrent admissions that don't otherwise contend on the same
    bed or patient (and so aren't serialized by that FOR UPDATE lock / by
    `_lock_patient_admission_slot`) could compute the same number and fail
    on `ipd_admissions.admission_number`'s unique constraint. Acquired last
    in `create_admission`, after the patient and bed locks, so lock order
    stays consistent across the whole function.
    """
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": f"ipd-admission-number:{tenant_id}"}
    )


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


async def _get_bed_or_404(db: AsyncSession, bed_id: uuid.UUID, *, for_update: bool = False) -> Bed:
    stmt = select(Bed).where(Bed.id == bed_id)
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
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
    bed = await _get_bed_or_404(db, bed_id, for_update=True)
    ensure_same_tenant(bed.tenant_id, current_user)
    ensure_same_facility(bed.facility_id, current_user)

    current_status = bed.status
    before = {"status": current_status, "is_active": bed.is_active, "bed_number": bed.bed_number}
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
        before=before,
        after={"status": bed.status, "is_active": bed.is_active, "bed_number": bed.bed_number},
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


async def _get_admission_or_404(
    db: AsyncSession, admission_id: uuid.UUID, *, for_update: bool = False
) -> Admission:
    stmt = select(Admission).where(Admission.id == admission_id)
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
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
    # Locks acquired in a fixed order (patient, then bed) so this can never
    # deadlock against itself under concurrent admits - see
    # `_lock_patient_admission_slot`. Both checks below are re-validated
    # against the now-locked, freshly-read rows, not the pre-lock reads.
    await _lock_patient_admission_slot(db, payload.patient_id)

    existing_admission = await db.execute(
        select(Admission).where(
            Admission.tenant_id == current_user.tenant_id,
            Admission.patient_id == payload.patient_id,
            Admission.status == "ADMITTED",
        )
    )
    if existing_admission.scalar_one_or_none() is not None:
        raise ConflictError("This patient already has an active admission.")

    bed = await _get_bed_or_404(db, payload.bed_id, for_update=True)
    ensure_same_tenant(bed.tenant_id, current_user)
    ensure_same_facility(bed.facility_id, current_user)

    if bed.status not in _ALLOCATABLE_BED_STATUSES:
        raise ConflictError("This bed is not available for admission.")

    await _lock_admission_number_sequence(db, current_user.tenant_id)
    admission = Admission(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        patient_id=payload.patient_id,
        admitting_doctor_id=payload.admitting_doctor_id,
        department_id=payload.department_id,
        admission_type=payload.admission_type,
        referral_source=payload.referral_source,
        referral_detail=payload.referral_detail,
        payment_category=payload.payment_category,
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

    if payload.deposit_amount is not None:
        db.add(
            Deposit(
                tenant_id=current_user.tenant_id,
                facility_id=current_user.facility_id,
                admission_id=admission.id,
                received_by=current_user.id,
                amount=payload.deposit_amount,
                payment_mode=payload.deposit_payment_mode,
            )
        )
    await db.flush()

    await audit_service.record_event(
        db,
        action="ipd.admission_created",
        resource_type="ipd_admission",
        resource_id=admission.id,
        # Scalar fields only, not `AdmissionOut.model_validate(admission)` -
        # `bed_assignments`/`deposits` are `lazy="selectin"` relationships
        # that were never populated by a query on this just-flushed object
        # (only committed rows get selectin-loaded), so validating the full
        # schema here raises MissingGreenlet under the async engine.
        after={
            "admission_number": admission.admission_number,
            "patient_id": str(admission.patient_id),
            "bed_id": str(bed.id),
            "admission_type": admission.admission_type,
            "payment_category": admission.payment_category,
        },
        commit=False,
    )
    await db.commit()
    await db.refresh(admission)
    return AdmissionOut.model_validate(admission)


async def update_admission(
    db: AsyncSession, admission_id: uuid.UUID, payload: AdmissionUpdateRequest, current_user: User
) -> AdmissionOut:
    admission = await _get_admission_or_404(db, admission_id, for_update=True)
    ensure_same_tenant(admission.tenant_id, current_user)
    ensure_same_facility(admission.facility_id, current_user)

    if admission.status != "ADMITTED":
        raise ConflictError("Only an active admission can be updated.")

    before = AdmissionOut.model_validate(admission).model_dump(mode="json")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(admission, field, value)
    await db.flush()

    await audit_service.record_event(
        db,
        action="ipd.admission_updated",
        resource_type="ipd_admission",
        resource_id=admission.id,
        before=before,
        after=AdmissionOut.model_validate(admission).model_dump(mode="json"),
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
    # Locks acquired in a fixed order (admission, then bed(s)) - matches
    # `update_admission`/`create_discharge`, so none of these can deadlock
    # against each other under concurrent requests.
    admission = await _get_admission_or_404(db, admission_id, for_update=True)
    ensure_same_tenant(admission.tenant_id, current_user)
    ensure_same_facility(admission.facility_id, current_user)

    if admission.status != "ADMITTED":
        raise ConflictError("Only an active admission can be transferred.")

    current_assignment = _active_assignment(admission)
    if current_assignment is None:
        raise ConflictError("This admission has no active bed assignment.")

    from_bed_id = current_assignment.bed_id
    to_bed_id = payload.to_bed_id
    if to_bed_id == from_bed_id:
        raise AppError("The destination bed must be different from the current bed.", code="VALIDATION_ERROR")

    # Both beds are locked in a fixed order by id - not "to then from" -
    # so this can't deadlock against a concurrent transfer swapping the
    # same two beds in the opposite direction.
    locked_beds = {
        bed_id: await _get_bed_or_404(db, bed_id, for_update=True)
        for bed_id in sorted({from_bed_id, to_bed_id}, key=str)
    }

    # Validate source bed: must belong to this tenant/facility and must
    # actually be the bed the admission is occupying. This should always
    # hold given the invariants elsewhere in this module, but a transfer is
    # destructive enough (it releases the source bed) that it's worth
    # confirming rather than assuming.
    from_bed = locked_beds[from_bed_id]
    ensure_same_tenant(from_bed.tenant_id, current_user)
    ensure_same_facility(from_bed.facility_id, current_user)
    if from_bed.status != "OCCUPIED":
        raise ConflictError("The source bed is not currently occupied.")

    # Validate destination bed: must belong to this tenant/facility and be
    # in an allocatable state.
    to_bed = locked_beds[to_bed_id]
    ensure_same_tenant(to_bed.tenant_id, current_user)
    ensure_same_facility(to_bed.facility_id, current_user)
    if to_bed.status not in _ALLOCATABLE_BED_STATUSES:
        raise ConflictError("The target bed is not available.")

    before = {
        "from_bed_id": str(from_bed.id),
        "from_bed_status": from_bed.status,
        "to_bed_id": str(to_bed.id),
        "to_bed_status": to_bed.status,
    }

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
        before=before,
        after=TransferOut.model_validate(transfer).model_dump(mode="json"),
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
    admission = await _get_admission_or_404(db, admission_id, for_update=True)
    ensure_same_tenant(admission.tenant_id, current_user)
    ensure_same_facility(admission.facility_id, current_user)

    if admission.status != "ADMITTED":
        raise ConflictError("This admission is not currently active.")

    # Billing validation is intentionally out of scope here - there is no
    # invoicing/charges module yet (P4-B06), so there is nothing real to
    # validate the discharge against. Once one exists, this is where a
    # "must be billed/cleared before discharge" gate belongs.
    before = {"admission_status": admission.status}

    current_assignment = _active_assignment(admission)
    if current_assignment is not None:
        bed = await _get_bed_or_404(db, current_assignment.bed_id, for_update=True)
        before["bed_id"] = str(bed.id)
        before["bed_status"] = bed.status
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
        before=before,
        after=DischargeOut.model_validate(discharge).model_dump(mode="json") | {"admission_status": admission.status},
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
        after=ConsentOut.model_validate(consent).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(consent)
    return ConsentOut.model_validate(consent)


# ---------------------------------------------------------------------------
# Deposit
# ---------------------------------------------------------------------------


async def list_deposits(db: AsyncSession, admission_id: uuid.UUID, current_user: User) -> list[DepositOut]:
    admission = await _get_admission_or_404(db, admission_id)
    ensure_same_tenant(admission.tenant_id, current_user)
    ensure_same_facility(admission.facility_id, current_user)

    result = await db.execute(
        select(Deposit).where(Deposit.admission_id == admission_id).order_by(Deposit.recorded_at)
    )
    return [DepositOut.model_validate(deposit) for deposit in result.scalars().all()]


async def create_deposit(
    db: AsyncSession, admission_id: uuid.UUID, payload: DepositCreateRequest, current_user: User
) -> DepositOut:
    admission = await _get_admission_or_404(db, admission_id)
    ensure_same_tenant(admission.tenant_id, current_user)
    ensure_same_facility(admission.facility_id, current_user)

    if admission.status != "ADMITTED":
        raise ConflictError("Deposits can only be recorded for an active admission.")

    deposit = Deposit(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        admission_id=admission.id,
        received_by=current_user.id,
        **payload.model_dump(),
    )
    db.add(deposit)
    await db.flush()

    await audit_service.record_event(
        db,
        action="ipd.deposit_recorded",
        resource_type="ipd_admission",
        resource_id=admission.id,
        after=DepositOut.model_validate(deposit).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(deposit)
    return DepositOut.model_validate(deposit)
