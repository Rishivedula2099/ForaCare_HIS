import uuid
from datetime import date, datetime, timezone

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import ensure_same_facility, ensure_same_tenant
from app.modules.audit import service as audit_service
from app.modules.auth.models import User
from app.modules.facilities.models import Facility
from app.modules.files import service as files_service
from app.modules.patients.models import (
    Patient,
    PatientAddress,
    PatientContact,
    PatientIdentifier,
    PatientPhoto,
)
from app.modules.patients.schemas import (
    PatientCreateRequest,
    PatientListItem,
    PatientOut,
    PatientUpdateRequest,
)

MINOR_AGE_YEARS = 18


def _calculate_age_years(dob: date) -> int:
    today = date.today()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


async def _generate_uid_and_mrn(db: AsyncSession, tenant_id: uuid.UUID, facility: Facility) -> tuple[str, str]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(func.count())
        .select_from(Patient)
        .where(
            Patient.facility_id == facility.id,
            extract("year", Patient.created_at) == now.year,
            extract("month", Patient.created_at) == now.month,
        )
    )
    sequence = (result.scalar_one() or 0) + 1
    seq_str = str(sequence).zfill(6)
    uid = f"{facility.facility_code}-{now.strftime('%Y%m')}-{seq_str}"
    mrn = f"MRN-{now.year}-{seq_str}"
    return uid, mrn


async def find_duplicate_patients(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    mobile: str | None = None,
    id_number: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    dob: date | None = None,
) -> list[PatientOut]:
    """Mirrors the frontend's `checkDuplicates`: mobile match, identity-number
    match, or name + birth-year match - see REQ-PAT-02."""
    matches: dict[uuid.UUID, Patient] = {}

    if mobile:
        result = await db.execute(
            select(Patient)
            .join(PatientContact, PatientContact.patient_id == Patient.id)
            .where(Patient.tenant_id == tenant_id, PatientContact.value == mobile)
        )
        for patient in result.scalars().unique().all():
            matches[patient.id] = patient

    if id_number:
        result = await db.execute(
            select(Patient)
            .join(PatientIdentifier, PatientIdentifier.patient_id == Patient.id)
            .where(Patient.tenant_id == tenant_id, PatientIdentifier.id_number == id_number)
        )
        for patient in result.scalars().unique().all():
            matches[patient.id] = patient

    if first_name and last_name and dob:
        result = await db.execute(
            select(Patient).where(
                Patient.tenant_id == tenant_id,
                func.lower(Patient.first_name) == first_name.lower(),
                func.lower(Patient.last_name) == last_name.lower(),
                extract("year", Patient.dob) == dob.year,
            )
        )
        for patient in result.scalars().unique().all():
            matches[patient.id] = patient

    return [PatientOut.model_validate(patient) for patient in matches.values()]


async def list_patients(
    db: AsyncSession,
    current_user: User,
    *,
    uid: str | None = None,
    mrn: str | None = None,
    name: str | None = None,
    mobile: str | None = None,
) -> list[PatientListItem]:
    stmt = select(Patient).where(
        Patient.tenant_id == current_user.tenant_id,
        Patient.facility_id == current_user.facility_id,
    )

    if uid:
        stmt = stmt.where(Patient.uid.ilike(f"%{uid}%"))
    if mrn:
        stmt = stmt.where(Patient.mrn.ilike(f"%{mrn}%"))
    if name:
        pattern = f"%{name}%"
        stmt = stmt.where(
            (Patient.first_name.ilike(pattern))
            | (Patient.last_name.ilike(pattern))
            | (func.concat(Patient.first_name, " ", Patient.last_name).ilike(pattern))
        )
    if mobile:
        stmt = stmt.join(PatientContact, PatientContact.patient_id == Patient.id).where(
            PatientContact.value.ilike(f"%{mobile}%")
        )

    stmt = stmt.order_by(Patient.created_at.desc())

    result = await db.execute(stmt)
    return [PatientListItem.model_validate(patient) for patient in result.scalars().unique().all()]


async def _get_patient_or_404(db: AsyncSession, patient_id: uuid.UUID) -> Patient:
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if patient is None:
        raise NotFoundError("Patient not found.")
    return patient


async def get_patient(db: AsyncSession, patient_id: uuid.UUID, current_user: User) -> PatientOut:
    patient = await _get_patient_or_404(db, patient_id)
    ensure_same_tenant(patient.tenant_id, current_user)

    await audit_service.record_event(
        db,
        action="patients.viewed",
        resource_type="patient",
        resource_id=patient.id,
        commit=False,
    )
    await db.commit()

    return PatientOut.model_validate(patient)


async def create_patient(
    db: AsyncSession, payload: PatientCreateRequest, current_user: User
) -> PatientOut:
    mobile = next((c.value for c in payload.contacts if c.contact_type == "MOBILE"), None)
    primary_identifier = payload.identifiers[0] if payload.identifiers else None

    duplicates = await find_duplicate_patients(
        db,
        current_user.tenant_id,
        mobile=mobile,
        id_number=primary_identifier.id_number if primary_identifier else None,
        first_name=payload.first_name,
        last_name=payload.last_name,
        dob=payload.dob,
    )
    if duplicates:
        raise ConflictError("A patient matching this mobile number, ID, or name and birth year already exists.")

    facility_result = await db.execute(
        select(Facility).where(Facility.id == current_user.facility_id)
    )
    facility = facility_result.scalar_one_or_none()
    if facility is None:
        raise NotFoundError("Registering facility not found.")

    uid, mrn = await _generate_uid_and_mrn(db, current_user.tenant_id, facility)

    patient = Patient(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        uid=uid,
        mrn=mrn,
        title=payload.title,
        first_name=payload.first_name,
        middle_name=payload.middle_name,
        last_name=payload.last_name,
        gender=payload.gender,
        dob=payload.dob,
        blood_group=payload.blood_group,
        marital_status=payload.marital_status,
        occupation=payload.occupation,
        preferred_language=payload.preferred_language,
        is_minor=_calculate_age_years(payload.dob) < MINOR_AGE_YEARS,
        guardian_name=payload.guardian_name,
        guardian_relationship=payload.guardian_relationship,
        guardian_phone=payload.guardian_phone,
        guardian_address=payload.guardian_address,
        registered_by=current_user.id,
    )
    patient.address = PatientAddress(**payload.address.model_dump())
    patient.contacts = [PatientContact(**contact.model_dump()) for contact in payload.contacts]
    patient.identifiers = [
        PatientIdentifier(**identifier.model_dump()) for identifier in payload.identifiers
    ]
    # A brand-new patient has no photos/identity links yet. Assigning empty
    # collections here (rather than leaving them unset) avoids the ORM
    # triggering a lazy fetch on first access below, which fails under the
    # async engine (MissingGreenlet) since this object was never loaded via
    # a SELECT that would have eager-loaded them.
    patient.photos = []
    patient.identity_links = []

    db.add(patient)
    await db.flush()

    await audit_service.record_event(
        db,
        action="patients.created",
        resource_type="patient",
        resource_id=patient.id,
        after=PatientOut.model_validate(patient).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(patient)

    return PatientOut.model_validate(patient)


async def upload_patient_photo(
    db: AsyncSession,
    patient_id: uuid.UUID,
    current_user: User,
    *,
    content_type: str | None,
    raw_bytes: bytes,
) -> PatientPhoto:
    patient = await _get_patient_or_404(db, patient_id)
    ensure_same_tenant(patient.tenant_id, current_user)
    ensure_same_facility(patient.facility_id, current_user)

    storage_path, resolved_content_type = files_service.validate_and_store_photo(
        tenant_id=patient.tenant_id,
        facility_id=patient.facility_id,
        patient_id=patient.id,
        content_type=content_type,
        raw_bytes=raw_bytes,
    )

    for existing in patient.photos:
        existing.is_primary = False

    photo = PatientPhoto(
        patient_id=patient.id,
        storage_path=storage_path,
        content_type=resolved_content_type,
        is_primary=True,
    )
    db.add(photo)
    await db.flush()

    await audit_service.record_event(
        db,
        action="patients.photo_uploaded",
        resource_type="patient",
        resource_id=patient.id,
        after={"photo_id": str(photo.id), "content_type": resolved_content_type},
        commit=False,
    )
    await db.commit()
    await db.refresh(photo)

    return photo


async def get_patient_photo_file(
    db: AsyncSession, patient_id: uuid.UUID, photo_id: uuid.UUID, current_user: User
) -> PatientPhoto:
    patient = await _get_patient_or_404(db, patient_id)
    ensure_same_tenant(patient.tenant_id, current_user)
    ensure_same_facility(patient.facility_id, current_user)

    photo = next((p for p in patient.photos if p.id == photo_id), None)
    if photo is None:
        raise NotFoundError("Photo not found.")

    await audit_service.record_event(
        db,
        action="patients.photo_accessed",
        resource_type="patient",
        resource_id=patient.id,
        after={"photo_id": str(photo.id)},
        commit=False,
    )
    await db.commit()

    return photo


async def update_patient(
    db: AsyncSession, patient_id: uuid.UUID, payload: PatientUpdateRequest, current_user: User
) -> PatientOut:
    patient = await _get_patient_or_404(db, patient_id)
    ensure_same_tenant(patient.tenant_id, current_user)

    before = PatientOut.model_validate(patient).model_dump(mode="json")

    scalar_fields = payload.model_dump(exclude={"address", "contacts", "identifiers"}, exclude_unset=True)
    for field, value in scalar_fields.items():
        setattr(patient, field, value)

    if "dob" in scalar_fields:
        patient.is_minor = _calculate_age_years(patient.dob) < MINOR_AGE_YEARS

    if payload.address is not None:
        if patient.address is None:
            patient.address = PatientAddress(**payload.address.model_dump())
        else:
            for field, value in payload.address.model_dump().items():
                setattr(patient.address, field, value)

    if payload.contacts is not None:
        patient.contacts = [PatientContact(**contact.model_dump()) for contact in payload.contacts]

    if payload.identifiers is not None:
        patient.identifiers = [
            PatientIdentifier(**identifier.model_dump()) for identifier in payload.identifiers
        ]

    await db.flush()
    after = PatientOut.model_validate(patient).model_dump(mode="json")

    await audit_service.record_event(
        db,
        action="patients.updated",
        resource_type="patient",
        resource_id=patient.id,
        before=before,
        after=after,
        commit=False,
    )
    await db.commit()
    await db.refresh(patient)

    return PatientOut.model_validate(patient)
