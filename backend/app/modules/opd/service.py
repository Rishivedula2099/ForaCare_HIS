import logging
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import case, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import ensure_same_facility, ensure_same_tenant
from app.modules.audit import service as audit_service
from app.modules.auth.models import User
from app.modules.departments.models import Department
from app.modules.doctors.models import Doctor
from app.modules.facilities.models import Facility
from app.modules.opd.models import Consultation, OPDEncounter, Prescription, PrescriptionItem, Token
from app.modules.opd.qr_security import generate_qr_reference, verify_qr_signature
from app.modules.opd.schemas import (
    ConsultationCreateRequest,
    ConsultationOut,
    ConsultationUpdateRequest,
    EncounterCreateRequest,
    EncounterOut,
    PrescriptionCreateRequest,
    PrescriptionOut,
    PrescriptionUpdateRequest,
    QRVerifyResult,
)
from app.modules.opd.ws_manager import manager as queue_ws_manager
from app.modules.patients.models import Patient

logger = logging.getLogger(__name__)

VISIT_TYPES = {"WALK_IN", "APPOINTMENT"}
PRIORITY_LEVELS = {"NORMAL", "PRIORITY"}
_PRIORITY_RANK = case((Token.priority == "PRIORITY", 0), else_=1)

# The token state machine (P3-B02). Every transition goes through
# `update_token_status`/`call_next_token`, which is the only place that may
# write `Token.status` - so this map is a complete description of what's
# reachable from where. SKIPPED can be re-queued (back to WAITING);
# COMPLETED/CANCELLED are terminal.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "WAITING": {"CALLED", "SKIPPED", "CANCELLED"},
    "CALLED": {"IN_CONSULTATION", "SKIPPED", "CANCELLED"},
    "IN_CONSULTATION": {"COMPLETED", "CANCELLED"},
    "SKIPPED": {"WAITING", "CANCELLED"},
    "COMPLETED": set(),
    "CANCELLED": set(),
}
_ACTIVE_TOKEN_STATUSES = {"CALLED", "IN_CONSULTATION"}

_ENCOUNTER_LOAD_OPTIONS = (
    selectinload(OPDEncounter.patient),
    selectinload(OPDEncounter.department),
    selectinload(OPDEncounter.doctor).selectinload(Doctor.department),
    selectinload(OPDEncounter.token),
)


async def _lock_doctor_queue(db: AsyncSession, doctor_id: uuid.UUID, day: date) -> None:
    """Serializes token numbering and queue-advancement for one doctor's day.

    Postgres transaction-scoped advisory lock (auto-released on commit/
    rollback) keyed by a hash of (doctor_id, day) - this is what actually
    protects against two concurrent registrations/call-next requests for the
    same doctor computing the same "next" number (P3-B02 concurrency
    protection). A `SELECT ... FOR UPDATE` on existing rows can't cover this
    because the very first token of the day has no row yet to lock.
    """
    lock_key = f"opd-queue:{doctor_id}:{day.isoformat()}"
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": lock_key})


async def _broadcast_queue_update(doctor_id: uuid.UUID) -> None:
    """Best-effort push notification (P3-B03) telling anyone watching this
    doctor's queue to refetch it. Never raises - a dropped/slow websocket
    push must not fail the underlying mutation, and the frontend's polling
    fallback covers a missed message anyway."""
    try:
        await queue_ws_manager.broadcast(str(doctor_id), {"type": "queue_updated", "doctor_id": str(doctor_id)})
    except Exception:
        logger.warning("Failed to broadcast OPD queue update for doctor %s", doctor_id, exc_info=True)


async def _generate_encounter_number(db: AsyncSession, facility: Facility, today: date) -> str:
    result = await db.execute(
        select(func.count())
        .select_from(OPDEncounter)
        .where(
            OPDEncounter.facility_id == facility.id,
            func.date(OPDEncounter.created_at) == today,
        )
    )
    sequence = (result.scalar_one() or 0) + 1
    return f"OPD-{facility.facility_code}-{today.strftime('%Y%m%d')}-{str(sequence).zfill(4)}"


async def _generate_token_number(db: AsyncSession, doctor_id: uuid.UUID, today: date) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(Token)
        .where(Token.doctor_id == doctor_id, Token.token_date == today)
    )
    return (result.scalar_one() or 0) + 1


async def register_visit(
    db: AsyncSession, payload: EncounterCreateRequest, current_user: User
) -> EncounterOut:
    if payload.visit_type not in VISIT_TYPES:
        raise AppError(
            f"Visit type must be one of: {', '.join(sorted(VISIT_TYPES))}.", code="VALIDATION_ERROR"
        )
    if payload.priority not in PRIORITY_LEVELS:
        raise AppError(
            f"Priority must be one of: {', '.join(sorted(PRIORITY_LEVELS))}.", code="VALIDATION_ERROR"
        )

    patient_result = await db.execute(select(Patient).where(Patient.id == payload.patient_id))
    patient = patient_result.scalar_one_or_none()
    if patient is None:
        raise NotFoundError("Patient not found.")
    ensure_same_tenant(patient.tenant_id, current_user)
    ensure_same_facility(patient.facility_id, current_user)

    department_result = await db.execute(
        select(Department).where(Department.id == payload.department_id)
    )
    department = department_result.scalar_one_or_none()
    if department is None:
        raise NotFoundError("Department not found.")
    ensure_same_tenant(department.tenant_id, current_user)
    ensure_same_facility(department.facility_id, current_user)
    if not department.is_active:
        raise AppError("The selected department is not active.", code="VALIDATION_ERROR")

    doctor_result = await db.execute(select(Doctor).where(Doctor.id == payload.doctor_id))
    doctor = doctor_result.scalar_one_or_none()
    if doctor is None:
        raise NotFoundError("Doctor not found.")
    ensure_same_tenant(doctor.tenant_id, current_user)
    ensure_same_facility(doctor.facility_id, current_user)
    if not doctor.is_active:
        raise AppError("The selected doctor is not active.", code="VALIDATION_ERROR")
    if doctor.department_id != department.id:
        raise AppError(
            "The selected doctor does not belong to the selected department.", code="VALIDATION_ERROR"
        )

    facility_result = await db.execute(
        select(Facility).where(Facility.id == current_user.facility_id)
    )
    facility = facility_result.scalar_one_or_none()
    if facility is None:
        raise NotFoundError("Facility not found.")

    today = datetime.now(timezone.utc).date()

    # Everything from here on must run after the advisory lock is taken and
    # before commit, so concurrent registrations for the same doctor/day
    # can't read the same "next" token number.
    await _lock_doctor_queue(db, doctor.id, today)

    encounter_number = await _generate_encounter_number(db, facility, today)

    encounter = OPDEncounter(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        patient_id=patient.id,
        department_id=department.id,
        doctor_id=doctor.id,
        registered_by=current_user.id,
        encounter_number=encounter_number,
        visit_type=payload.visit_type,
        scheduled_at=payload.scheduled_at,
        notes=payload.notes,
        qr_code=generate_qr_reference(),
    )
    db.add(encounter)
    await db.flush()

    token_number = await _generate_token_number(db, doctor.id, today)
    token = Token(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        encounter_id=encounter.id,
        doctor_id=doctor.id,
        token_date=today,
        token_number=token_number,
        priority=payload.priority,
    )
    db.add(token)
    await db.flush()

    await audit_service.record_event(
        db,
        action="opd.encounters.registered",
        resource_type="opd_encounter",
        resource_id=encounter.id,
        after={
            "encounter_number": encounter.encounter_number,
            "patient_id": str(patient.id),
            "doctor_id": str(doctor.id),
            "department_id": str(department.id),
            "token_number": token.token_number,
            "priority": token.priority,
        },
        commit=False,
    )
    await db.commit()
    await _broadcast_queue_update(doctor.id)

    return await get_encounter(db, encounter.id, current_user)


async def _get_encounter_or_404(db: AsyncSession, encounter_id: uuid.UUID) -> OPDEncounter:
    result = await db.execute(
        select(OPDEncounter).where(OPDEncounter.id == encounter_id).options(*_ENCOUNTER_LOAD_OPTIONS)
    )
    encounter = result.scalar_one_or_none()
    if encounter is None:
        raise NotFoundError("OPD encounter not found.")
    return encounter


async def get_encounter(
    db: AsyncSession, encounter_id: uuid.UUID, current_user: User
) -> EncounterOut:
    encounter = await _get_encounter_or_404(db, encounter_id)
    ensure_same_tenant(encounter.tenant_id, current_user)
    ensure_same_facility(encounter.facility_id, current_user)
    return EncounterOut.model_validate(encounter)


async def list_encounters(
    db: AsyncSession,
    current_user: User,
    *,
    patient_id: uuid.UUID | None = None,
    doctor_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    visit_date: date | None = None,
) -> list[EncounterOut]:
    stmt = (
        select(OPDEncounter)
        .where(
            OPDEncounter.tenant_id == current_user.tenant_id,
            OPDEncounter.facility_id == current_user.facility_id,
        )
        .options(*_ENCOUNTER_LOAD_OPTIONS)
    )
    if patient_id:
        stmt = stmt.where(OPDEncounter.patient_id == patient_id)
    if doctor_id:
        stmt = stmt.where(OPDEncounter.doctor_id == doctor_id)
    if department_id:
        stmt = stmt.where(OPDEncounter.department_id == department_id)
    if visit_date:
        stmt = stmt.where(func.date(OPDEncounter.created_at) == visit_date)
    stmt = stmt.order_by(OPDEncounter.created_at.desc())

    result = await db.execute(stmt)
    return [EncounterOut.model_validate(encounter) for encounter in result.scalars().unique().all()]


async def _get_doctor_or_404(
    db: AsyncSession, doctor_id: uuid.UUID, current_user: User
) -> Doctor:
    doctor_result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
    doctor = doctor_result.scalar_one_or_none()
    if doctor is None:
        raise NotFoundError("Doctor not found.")
    ensure_same_tenant(doctor.tenant_id, current_user)
    ensure_same_facility(doctor.facility_id, current_user)
    return doctor


async def get_doctor_for_queue_access(db: AsyncSession, current_user: User, doctor_id: uuid.UUID) -> Doctor:
    """Public wrapper around `_get_doctor_or_404` for callers outside this
    module that only need the tenant/facility access check (e.g. the queue
    WebSocket route in app/api/v1/opd.py, which has no encounter/token to
    check against)."""
    return await _get_doctor_or_404(db, doctor_id, current_user)


async def get_doctor_queue(
    db: AsyncSession, current_user: User, doctor_id: uuid.UUID, queue_date: date
) -> list[EncounterOut]:
    await _get_doctor_or_404(db, doctor_id, current_user)

    # Priority tokens surface ahead of normal ones within the queue; ties
    # (and normal-vs-normal ordering) fall back to registration order via
    # `token_number` - see P3-B02 "Priority".
    stmt = (
        select(OPDEncounter)
        .join(Token, Token.encounter_id == OPDEncounter.id)
        .where(OPDEncounter.doctor_id == doctor_id, Token.token_date == queue_date)
        .options(*_ENCOUNTER_LOAD_OPTIONS)
        .order_by(_PRIORITY_RANK, Token.token_number)
    )
    result = await db.execute(stmt)
    return [EncounterOut.model_validate(encounter) for encounter in result.scalars().unique().all()]


async def call_next_token(
    db: AsyncSession, current_user: User, doctor_id: uuid.UUID, queue_date: date
) -> EncounterOut:
    doctor = await _get_doctor_or_404(db, doctor_id, current_user)

    await _lock_doctor_queue(db, doctor.id, queue_date)

    active_result = await db.execute(
        select(Token).where(
            Token.doctor_id == doctor.id,
            Token.token_date == queue_date,
            Token.status.in_(_ACTIVE_TOKEN_STATUSES),
        )
    )
    if active_result.scalar_one_or_none() is not None:
        raise ConflictError(
            "This doctor already has an active token. Complete or skip it before calling the next one."
        )

    next_result = await db.execute(
        select(Token)
        .where(Token.doctor_id == doctor.id, Token.token_date == queue_date, Token.status == "WAITING")
        .order_by(_PRIORITY_RANK, Token.token_number)
        .limit(1)
        .with_for_update()
    )
    token = next_result.scalar_one_or_none()
    if token is None:
        raise AppError("There are no waiting tokens in this doctor's queue.", code="QUEUE_EMPTY")

    before_status = token.status
    token.status = "CALLED"
    token.called_at = datetime.now(timezone.utc)
    await db.flush()

    await audit_service.record_event(
        db,
        action="opd.tokens.called",
        resource_type="opd_token",
        resource_id=token.id,
        before={"status": before_status},
        after={"status": token.status, "token_number": token.token_number},
        commit=False,
    )
    await db.commit()
    await _broadcast_queue_update(doctor.id)

    return await get_encounter(db, token.encounter_id, current_user)


async def update_token_status(
    db: AsyncSession, current_user: User, token_id: uuid.UUID, new_status: str
) -> EncounterOut:
    result = await db.execute(select(Token).where(Token.id == token_id).with_for_update())
    token = result.scalar_one_or_none()
    if token is None:
        raise NotFoundError("Token not found.")
    ensure_same_tenant(token.tenant_id, current_user)
    ensure_same_facility(token.facility_id, current_user)

    if new_status not in ALLOWED_TRANSITIONS:
        raise AppError(f"Unknown token status: {new_status}.", code="VALIDATION_ERROR")

    allowed_next = ALLOWED_TRANSITIONS[token.status]
    if new_status not in allowed_next:
        raise AppError(
            f"Cannot move a token from {token.status} to {new_status}.", code="INVALID_TRANSITION"
        )

    before_status = token.status
    now = datetime.now(timezone.utc)
    token.status = new_status
    if new_status == "IN_CONSULTATION":
        token.started_at = now
    elif new_status == "COMPLETED":
        token.completed_at = now
    elif new_status == "WAITING":
        # Re-queued from SKIPPED - clear the earlier call/consult timestamps
        # so the token reads as freshly waiting again.
        token.called_at = None
        token.started_at = None

    encounter: OPDEncounter | None = None
    if new_status == "CANCELLED":
        # A cancelled visit's QR is no longer a valid check-in - revoke it
        # automatically rather than leaving a scannable QR for a visit that
        # isn't happening (P3-F04).
        encounter_result = await db.execute(
            select(OPDEncounter).where(OPDEncounter.id == token.encounter_id)
        )
        encounter = encounter_result.scalar_one_or_none()
        if encounter is not None and encounter.qr_status == "ACTIVE":
            encounter.qr_status = "REVOKED"
            encounter.qr_revoked_at = now

    await db.flush()

    await audit_service.record_event(
        db,
        action="opd.tokens.status_changed",
        resource_type="opd_token",
        resource_id=token.id,
        before={"status": before_status},
        after={"status": token.status},
        commit=False,
    )
    await db.commit()
    await _broadcast_queue_update(token.doctor_id)

    return await get_encounter(db, token.encounter_id, current_user)


async def revoke_qr(db: AsyncSession, current_user: User, encounter_id: uuid.UUID) -> EncounterOut:
    encounter = await _get_encounter_or_404(db, encounter_id)
    ensure_same_tenant(encounter.tenant_id, current_user)
    ensure_same_facility(encounter.facility_id, current_user)

    if encounter.qr_status == "REVOKED":
        raise AppError("This QR code has already been revoked.", code="ALREADY_REVOKED")

    encounter.qr_status = "REVOKED"
    encounter.qr_revoked_at = datetime.now(timezone.utc)
    await db.flush()

    await audit_service.record_event(
        db,
        action="opd.qr.revoked",
        resource_type="opd_encounter",
        resource_id=encounter.id,
        commit=False,
    )
    await db.commit()

    return await get_encounter(db, encounter.id, current_user)


async def verify_qr_code(db: AsyncSession, current_user: User, qr_code: str) -> QRVerifyResult:
    # Structural check first (P3-B06): a malformed/tampered/guessed reference
    # fails the HMAC comparison without ever touching the database.
    if not verify_qr_signature(qr_code):
        return QRVerifyResult(valid=False, reason="INVALID", encounter=None)

    result = await db.execute(
        select(OPDEncounter).where(OPDEncounter.qr_code == qr_code).options(*_ENCOUNTER_LOAD_OPTIONS)
    )
    encounter = result.scalar_one_or_none()

    # A QR for another tenant/facility reads identically to one that simply
    # doesn't exist - confirming cross-tenant existence would itself be a
    # data leak (same rationale as `ensure_same_tenant`'s 404).
    if (
        encounter is None
        or encounter.tenant_id != current_user.tenant_id
        or encounter.facility_id != current_user.facility_id
    ):
        return QRVerifyResult(valid=False, reason="INVALID", encounter=None)

    encounter_out = EncounterOut.model_validate(encounter)

    if encounter.qr_status == "REVOKED":
        return QRVerifyResult(valid=False, reason="REVOKED", encounter=encounter_out)

    if datetime.now(timezone.utc) > encounter.qr_expires_at:
        return QRVerifyResult(valid=False, reason="EXPIRED", encounter=encounter_out)

    await audit_service.record_event(
        db,
        action="opd.qr.verified",
        resource_type="opd_encounter",
        resource_id=encounter.id,
        commit=False,
    )
    await db.commit()

    return QRVerifyResult(valid=True, reason="OK", encounter=encounter_out)


# ---------------------------------------------------------------------------
# Consultation (P3-F05/P3-B04)
# ---------------------------------------------------------------------------

CONSULTATION_STATUSES = {"IN_PROGRESS", "COMPLETED"}
# Administrative roles may correct a consultation or prescription on a
# doctor's behalf (e.g. a documentation fix after the fact); every other
# role must be the exact doctor assigned to the encounter - see
# `_ensure_is_assigned_doctor`. Shared by both Consultation (P3-B04) and
# Prescription (P3-B05) enforcement.
_CLINICAL_RECORD_ADMIN_OVERRIDE_ROLES = {"SUPER_ADMIN", "HOSPITAL_ADMIN"}

_CONSULTATION_LOAD_OPTIONS = (
    selectinload(Consultation.encounter).selectinload(OPDEncounter.patient),
    selectinload(Consultation.encounter).selectinload(OPDEncounter.department),
    selectinload(Consultation.encounter).selectinload(OPDEncounter.doctor).selectinload(Doctor.department),
    selectinload(Consultation.encounter).selectinload(OPDEncounter.token),
    selectinload(Consultation.doctor),
)

_VITALS_FIELDS = (
    "temperature_celsius",
    "pulse_bpm",
    "bp_systolic",
    "bp_diastolic",
    "spo2_percent",
    "respiratory_rate",
    "weight_kg",
    "height_cm",
)


async def _ensure_is_assigned_doctor(
    db: AsyncSession, encounter: OPDEncounter, current_user: User, *, record_type: str
) -> None:
    """P3-B04/P3-B05 "enforce doctor permissions": beyond the RBAC
    `consultations.manage`/`prescriptions.manage` permission (checked by the
    route dependency), only the doctor actually assigned to this encounter
    may record or edit its consultation/prescription - a different doctor
    with the same permission must not be able to write into someone else's
    encounter."""
    if current_user.role.code in _CLINICAL_RECORD_ADMIN_OVERRIDE_ROLES:
        return
    result = await db.execute(select(Doctor).where(Doctor.id == encounter.doctor_id))
    doctor = result.scalar_one_or_none()
    if doctor is None or doctor.user_id != current_user.id:
        raise ForbiddenError(f"Only the doctor assigned to this encounter can record its {record_type}.")


def _apply_vitals(consultation: Consultation, vitals) -> None:
    """Sets only the vitals fields actually provided - a `None` field means
    "not entered yet", not "clear this value", so progressive form-filling
    (save what's known now, add more later) never wipes earlier entries."""
    if vitals is None:
        return
    for field in _VITALS_FIELDS:
        value = getattr(vitals, field)
        if value is not None:
            setattr(consultation, field, value)


def _consultation_audit_snapshot(consultation: Consultation) -> dict:
    snapshot = {
        "status": consultation.status,
        "chief_complaint": consultation.chief_complaint,
        "history": consultation.history,
        "examination": consultation.examination,
        "diagnosis": consultation.diagnosis,
        "allergies": consultation.allergies,
        "investigation": consultation.investigation,
        "treatment": consultation.treatment,
        "notes": consultation.notes,
    }
    for field in _VITALS_FIELDS:
        value = getattr(consultation, field)
        snapshot[field] = float(value) if value is not None else None
    return snapshot


async def _get_consultation_by_encounter_or_404(db: AsyncSession, encounter_id: uuid.UUID) -> Consultation:
    result = await db.execute(
        select(Consultation)
        .where(Consultation.encounter_id == encounter_id)
        .options(*_CONSULTATION_LOAD_OPTIONS)
    )
    consultation = result.scalar_one_or_none()
    if consultation is None:
        raise NotFoundError("No consultation has been recorded for this encounter yet.")
    return consultation


async def create_consultation(
    db: AsyncSession,
    current_user: User,
    encounter_id: uuid.UUID,
    payload: ConsultationCreateRequest,
) -> ConsultationOut:
    encounter = await _get_encounter_or_404(db, encounter_id)
    ensure_same_tenant(encounter.tenant_id, current_user)
    ensure_same_facility(encounter.facility_id, current_user)
    await _ensure_is_assigned_doctor(db, encounter, current_user, record_type="consultation")

    existing = await db.execute(select(Consultation).where(Consultation.encounter_id == encounter_id))
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A consultation already exists for this encounter.")

    consultation = Consultation(
        tenant_id=encounter.tenant_id,
        facility_id=encounter.facility_id,
        encounter_id=encounter.id,
        doctor_id=encounter.doctor_id,
        chief_complaint=payload.chief_complaint,
        history=payload.history,
        examination=payload.examination,
        diagnosis=payload.diagnosis,
        allergies=payload.allergies,
        investigation=payload.investigation,
        treatment=payload.treatment,
        notes=payload.notes,
        started_at=datetime.now(timezone.utc),
    )
    _apply_vitals(consultation, payload.vitals)
    db.add(consultation)
    await db.flush()

    await audit_service.record_event(
        db,
        action="opd.consultations.created",
        resource_type="opd_consultation",
        resource_id=consultation.id,
        after=_consultation_audit_snapshot(consultation),
        commit=False,
    )
    await db.commit()

    return await get_consultation(db, current_user, encounter_id)


async def get_consultation(
    db: AsyncSession, current_user: User, encounter_id: uuid.UUID
) -> ConsultationOut:
    consultation = await _get_consultation_by_encounter_or_404(db, encounter_id)
    ensure_same_tenant(consultation.tenant_id, current_user)
    ensure_same_facility(consultation.facility_id, current_user)
    return ConsultationOut.model_validate(consultation)


async def update_consultation(
    db: AsyncSession,
    current_user: User,
    encounter_id: uuid.UUID,
    payload: ConsultationUpdateRequest,
) -> ConsultationOut:
    consultation = await _get_consultation_by_encounter_or_404(db, encounter_id)
    ensure_same_tenant(consultation.tenant_id, current_user)
    ensure_same_facility(consultation.facility_id, current_user)
    await _ensure_is_assigned_doctor(db, consultation.encounter, current_user, record_type="consultation")

    before = _consultation_audit_snapshot(consultation)

    updates = payload.model_dump(exclude={"vitals", "status"}, exclude_unset=True)
    for field, value in updates.items():
        setattr(consultation, field, value)
    _apply_vitals(consultation, payload.vitals)

    just_completed = False
    if payload.status is not None:
        if payload.status not in CONSULTATION_STATUSES:
            raise AppError(
                f"Consultation status must be one of: {', '.join(sorted(CONSULTATION_STATUSES))}.",
                code="VALIDATION_ERROR",
            )
        consultation.status = payload.status
        if payload.status == "COMPLETED" and consultation.completed_at is None:
            consultation.completed_at = datetime.now(timezone.utc)
            just_completed = True

            # Finishing the consultation naturally finishes the visit's
            # token too, if the queue still has it as in-consultation -
            # ties this into the P3-B02 token state machine rather than
            # leaving the two to drift out of sync.
            token_result = await db.execute(
                select(Token).where(Token.encounter_id == consultation.encounter_id)
            )
            token = token_result.scalar_one_or_none()
            if token is not None and token.status == "IN_CONSULTATION":
                token.status = "COMPLETED"
                token.completed_at = consultation.completed_at

    await db.flush()

    await audit_service.record_event(
        db,
        action="opd.consultations.updated",
        resource_type="opd_consultation",
        resource_id=consultation.id,
        before=before,
        after=_consultation_audit_snapshot(consultation),
        commit=False,
    )
    await db.commit()

    if just_completed:
        await _broadcast_queue_update(consultation.doctor_id)

    return await get_consultation(db, current_user, encounter_id)


async def list_patient_consultation_history(
    db: AsyncSession, current_user: User, patient_id: uuid.UUID
) -> list[ConsultationOut]:
    stmt = (
        select(Consultation)
        .join(OPDEncounter, OPDEncounter.id == Consultation.encounter_id)
        .where(
            OPDEncounter.patient_id == patient_id,
            Consultation.tenant_id == current_user.tenant_id,
            Consultation.facility_id == current_user.facility_id,
        )
        .options(*_CONSULTATION_LOAD_OPTIONS)
        .order_by(Consultation.created_at.desc())
    )
    result = await db.execute(stmt)
    return [ConsultationOut.model_validate(consultation) for consultation in result.scalars().unique().all()]


# ---------------------------------------------------------------------------
# Prescription (P3-F06/P3-B05)
# ---------------------------------------------------------------------------

_PRESCRIPTION_LOAD_OPTIONS = (
    selectinload(Prescription.items),
    selectinload(Prescription.doctor),
    selectinload(Prescription.consultation).selectinload(Consultation.encounter),
)


def _build_prescription_item(item) -> PrescriptionItem:
    return PrescriptionItem(
        drug_name=item.drug_name,
        dosage=item.dosage,
        route=item.route.value,
        frequency=item.frequency,
        duration=item.duration,
        instructions=item.instructions,
    )


def _prescription_audit_snapshot(prescription: Prescription) -> dict:
    return {
        "items": [
            {
                "drug_name": item.drug_name,
                "dosage": item.dosage,
                "route": item.route,
                "frequency": item.frequency,
                "duration": item.duration,
                "instructions": item.instructions,
            }
            for item in prescription.items
        ]
    }


async def _get_prescription_by_encounter_or_404(db: AsyncSession, encounter_id: uuid.UUID) -> Prescription:
    result = await db.execute(
        select(Prescription)
        .join(Consultation, Consultation.id == Prescription.consultation_id)
        .where(Consultation.encounter_id == encounter_id)
        .options(*_PRESCRIPTION_LOAD_OPTIONS)
    )
    prescription = result.scalar_one_or_none()
    if prescription is None:
        raise NotFoundError("No prescription has been recorded for this encounter yet.")
    return prescription


async def create_prescription(
    db: AsyncSession,
    current_user: User,
    encounter_id: uuid.UUID,
    payload: PrescriptionCreateRequest,
) -> PrescriptionOut:
    encounter = await _get_encounter_or_404(db, encounter_id)
    ensure_same_tenant(encounter.tenant_id, current_user)
    ensure_same_facility(encounter.facility_id, current_user)
    await _ensure_is_assigned_doctor(db, encounter, current_user, record_type="prescription")

    consultation_result = await db.execute(
        select(Consultation).where(Consultation.encounter_id == encounter_id)
    )
    consultation = consultation_result.scalar_one_or_none()
    if consultation is None:
        raise AppError(
            "Start the consultation before writing a prescription for this encounter.",
            code="VALIDATION_ERROR",
        )

    existing = await db.execute(
        select(Prescription).where(Prescription.consultation_id == consultation.id)
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A prescription already exists for this encounter.")

    prescription = Prescription(
        tenant_id=encounter.tenant_id,
        facility_id=encounter.facility_id,
        consultation_id=consultation.id,
        doctor_id=encounter.doctor_id,
        items=[_build_prescription_item(item) for item in payload.items],
    )
    db.add(prescription)
    await db.flush()

    await audit_service.record_event(
        db,
        action="opd.prescriptions.created",
        resource_type="opd_prescription",
        resource_id=prescription.id,
        after=_prescription_audit_snapshot(prescription),
        commit=False,
    )
    await db.commit()

    return await get_prescription(db, current_user, encounter_id)


async def get_prescription(
    db: AsyncSession, current_user: User, encounter_id: uuid.UUID
) -> PrescriptionOut:
    prescription = await _get_prescription_by_encounter_or_404(db, encounter_id)
    ensure_same_tenant(prescription.tenant_id, current_user)
    ensure_same_facility(prescription.facility_id, current_user)
    return PrescriptionOut.model_validate(prescription)


async def update_prescription(
    db: AsyncSession,
    current_user: User,
    encounter_id: uuid.UUID,
    payload: PrescriptionUpdateRequest,
) -> PrescriptionOut:
    prescription = await _get_prescription_by_encounter_or_404(db, encounter_id)
    ensure_same_tenant(prescription.tenant_id, current_user)
    ensure_same_facility(prescription.facility_id, current_user)
    await _ensure_is_assigned_doctor(
        db, prescription.consultation.encounter, current_user, record_type="prescription"
    )

    before = _prescription_audit_snapshot(prescription)

    # Full replace: simplest correct model for "the doctor edited the list
    # and resaved" - avoids diffing individual medicine lines. `items` has
    # cascade="all, delete-orphan" so old rows are actually removed, not
    # just unlinked.
    prescription.items = [_build_prescription_item(item) for item in payload.items]
    await db.flush()

    await audit_service.record_event(
        db,
        action="opd.prescriptions.updated",
        resource_type="opd_prescription",
        resource_id=prescription.id,
        before=before,
        after=_prescription_audit_snapshot(prescription),
        commit=False,
    )
    await db.commit()

    return await get_prescription(db, current_user, encounter_id)
