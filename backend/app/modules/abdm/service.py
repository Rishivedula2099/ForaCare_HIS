import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.permissions import ensure_same_facility, ensure_same_tenant
from app.modules.abdm.adapter import AbdmError
from app.modules.abdm.factory import get_abdm_adapter
from app.modules.abdm.models import AbhaConsent
from app.modules.abdm.schemas import AbhaStatusOut, ConsentOut, OtpChallengeOut
from app.modules.audit import service as audit_service
from app.modules.auth.models import User
from app.modules.patients.models import Patient, PatientIdentityLink

SYSTEM = "ABHA"


_GATEWAY_STATUS_CODES = {
    "ABDM_INVALID_OTP": 400,
    "ABDM_INVALID_TRANSACTION": 400,
    "ABDM_REJECTED": 400,
    "ABDM_TIMEOUT": 504,
    "ABDM_UNAVAILABLE": 503,
    "ABDM_AUTH_FAILED": 502,
    "ABDM_NOT_CONFIGURED": 503,
    "ABDM_NOT_IMPLEMENTED": 501,
}


def _gateway_error(exc: AbdmError) -> AppError:
    """Maps an adapter failure to an HTTP error. The `code` is what the UI
    keys its integration states on (timeout vs. unavailable vs. rejected)."""
    return AppError(exc.message, code=exc.code, status_code=_GATEWAY_STATUS_CODES.get(exc.code, 502))


async def _get_patient(db: AsyncSession, patient_id: uuid.UUID, user: User) -> Patient:
    patient = (await db.execute(select(Patient).where(Patient.id == patient_id))).scalar_one_or_none()
    if patient is None:
        raise NotFoundError("Patient not found.")
    ensure_same_tenant(patient.tenant_id, user)
    ensure_same_facility(patient.facility_id, user)  # P10-B02: found by the cross-facility matrix
    return patient


async def _get_patient_for_update(db: AsyncSession, patient_id: uuid.UUID, user: User) -> Patient:
    """Linking identity is a write: unlike read-only status, it is confined to
    the patient's own facility (same rule as billing), not the whole tenant."""
    patient = await _get_patient(db, patient_id, user)
    ensure_same_facility(patient.facility_id, user)
    return patient


def _mask(abha_number: str | None) -> str | None:
    """Audit trail keeps only the last 4 digits of a national identifier."""
    return f"**-****-****-{abha_number[-4:]}" if abha_number else None


async def _commit(db: AsyncSession) -> None:
    """The unique indexes are the final guard against two patients ending up
    with the same ABHA (or a patient with two) under concurrent requests."""
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ConflictError("This ABHA is already linked to a patient.") from exc


def _abha_link(patient: Patient) -> PatientIdentityLink | None:
    return next((link for link in patient.identity_links if link.system == SYSTEM), None)


async def _consents(db: AsyncSession, patient_id: uuid.UUID) -> list[AbhaConsent]:
    result = await db.execute(
        select(AbhaConsent).where(AbhaConsent.patient_id == patient_id).order_by(AbhaConsent.granted_at.desc())
    )
    return list(result.scalars())


async def _status(db: AsyncSession, patient: Patient) -> AbhaStatusOut:
    link = _abha_link(patient)
    return AbhaStatusOut(
        patient_id=patient.id,
        status=link.status if link else "UNVERIFIED",
        abha_number=link.external_id if link else None,
        abha_address=link.external_address if link else None,
        linked_at=link.linked_at if link else None,
        consents=[ConsentOut.model_validate(c) for c in await _consents(db, patient.id)],
    )


async def get_status(db: AsyncSession, patient_id: uuid.UUID, user: User) -> AbhaStatusOut:
    return await _status(db, await _get_patient(db, patient_id, user))


async def request_otp(auth_method: str, identifier: str) -> OtpChallengeOut:
    try:
        challenge = await get_abdm_adapter().request_otp(auth_method=auth_method, identifier=identifier)
    except AbdmError as exc:
        raise _gateway_error(exc) from exc
    return OtpChallengeOut(transaction_id=challenge.transaction_id, message=challenge.message)


async def verify(
    db: AsyncSession, patient_id: uuid.UUID, user: User, *, transaction_id: str, otp: str
) -> AbhaStatusOut:
    """Completes the OTP challenge and records the verified ABHA on the
    patient (status VERIFIED). Linking is a separate, explicit step."""
    patient = await _get_patient_for_update(db, patient_id, user)
    try:
        profile = await get_abdm_adapter().verify_otp(transaction_id=transaction_id, otp=otp)
    except AbdmError as exc:
        await db.rollback()
        await audit_service.record_event(
            db,
            action="abha.verification_failed",
            resource_type="patient",
            resource_id=patient_id,
            after={"error_code": exc.code},
        )
        raise _gateway_error(exc) from exc

    in_use = (
        await db.execute(
            select(PatientIdentityLink.id)
            .join(Patient, Patient.id == PatientIdentityLink.patient_id)
            .where(
                PatientIdentityLink.system == SYSTEM,
                PatientIdentityLink.external_id == profile.abha_number,
                PatientIdentityLink.patient_id != patient.id,
                Patient.tenant_id == patient.tenant_id,
            )
        )
    ).first()
    if in_use is not None:
        raise ConflictError("This ABHA number is already linked to another patient.")

    link = _abha_link(patient)
    if link is not None and link.status == "LINKED":
        if link.external_id != profile.abha_number:
            raise ConflictError("This patient already has a different ABHA linked. Unlink it first.")
        return await _status(db, patient)  # same ABHA re-verified: stays LINKED
    before = {"status": link.status} if link else None
    if link is None:
        link = PatientIdentityLink(patient_id=patient.id, system=SYSTEM)
        db.add(link)
        patient.identity_links.append(link)
    link.external_id = profile.abha_number
    link.external_address = profile.abha_address
    link.status = "VERIFIED"
    link.linked_at = None

    await audit_service.record_event(
        db,
        action="abha.verified",
        resource_type="patient",
        resource_id=patient.id,
        before=before,
        after={"status": "VERIFIED", "abha_number": _mask(profile.abha_number)},
        commit=False,
    )
    await _commit(db)
    return await _status(db, patient)


async def link(db: AsyncSession, patient_id: uuid.UUID, user: User) -> AbhaStatusOut:
    patient = await _get_patient_for_update(db, patient_id, user)
    abha = _abha_link(patient)
    if abha is None or abha.status not in ("VERIFIED", "LINKED"):
        raise ConflictError("Verify the patient's ABHA before linking it.")
    if abha.status != "LINKED":
        abha.status = "LINKED"
        abha.linked_at = datetime.now(timezone.utc)
        await audit_service.record_event(
            db,
            action="abha.linked",
            resource_type="patient",
            resource_id=patient.id,
            before={"status": "VERIFIED"},
            after={"status": "LINKED", "abha_number": _mask(abha.external_id)},
            commit=False,
        )
        await _commit(db)
    return await _status(db, patient)


async def unlink(db: AsyncSession, patient_id: uuid.UUID, user: User) -> AbhaStatusOut:
    """Clears the ABHA link and revokes every active consent - consent given
    against an ABHA must not outlive the link it was given for."""
    patient = await _get_patient_for_update(db, patient_id, user)
    abha = _abha_link(patient)
    if abha is None or abha.status == "UNVERIFIED":
        raise ConflictError("Patient has no ABHA to unlink.")
    now = datetime.now(timezone.utc)
    for consent in await _consents(db, patient.id):
        if consent.status == "GRANTED":
            consent.status = "REVOKED"
            consent.revoked_at = now
            consent.revoked_by = user.id
    previous = abha.status
    unlinked_number = abha.external_id
    abha.external_id = None
    abha.external_address = None
    abha.status = "UNVERIFIED"
    abha.linked_at = None
    await audit_service.record_event(
        db,
        action="abha.unlinked",
        resource_type="patient",
        resource_id=patient.id,
        before={"status": previous, "abha_number": _mask(unlinked_number)},
        after={"status": "UNVERIFIED"},
        commit=False,
    )
    await _commit(db)
    return await _status(db, patient)


async def grant_consent(db: AsyncSession, patient_id: uuid.UUID, user: User, *, purpose: str) -> ConsentOut:
    patient = await _get_patient_for_update(db, patient_id, user)
    abha = _abha_link(patient)
    if abha is None or abha.status != "LINKED":
        raise ConflictError("Link the patient's ABHA before recording consent.")
    if any(c.purpose == purpose and c.status == "GRANTED" for c in await _consents(db, patient.id)):
        raise ConflictError("Consent for this purpose is already granted.")
    consent = AbhaConsent(
        tenant_id=patient.tenant_id,
        facility_id=patient.facility_id,
        patient_id=patient.id,
        purpose=purpose,
        status="GRANTED",
        granted_by=user.id,
    )
    db.add(consent)
    await db.flush()
    await audit_service.record_event(
        db,
        action="abha.consent_granted",
        resource_type="patient",
        resource_id=patient.id,
        after={"consent_id": str(consent.id), "purpose": purpose},
        commit=False,
    )
    await _commit(db)
    await db.refresh(consent)
    return ConsentOut.model_validate(consent)


async def revoke_consent(
    db: AsyncSession, patient_id: uuid.UUID, consent_id: uuid.UUID, user: User
) -> ConsentOut:
    patient = await _get_patient_for_update(db, patient_id, user)
    consent = (
        await db.execute(
            select(AbhaConsent).where(AbhaConsent.id == consent_id, AbhaConsent.patient_id == patient.id)
        )
    ).scalar_one_or_none()
    if consent is None:
        raise NotFoundError("Consent not found.")
    if consent.status == "REVOKED":
        raise ConflictError("Consent is already revoked.")
    consent.status = "REVOKED"
    consent.revoked_at = datetime.now(timezone.utc)
    consent.revoked_by = user.id
    await audit_service.record_event(
        db,
        action="abha.consent_revoked",
        resource_type="patient",
        resource_id=patient.id,
        after={"consent_id": str(consent.id), "purpose": consent.purpose},
        commit=False,
    )
    await _commit(db)
    await db.refresh(consent)
    return ConsentOut.model_validate(consent)
