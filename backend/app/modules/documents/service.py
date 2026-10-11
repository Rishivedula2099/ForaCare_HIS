"""P7-B01: central document generation engine.

Every printable document goes through `generate_document`, which owns the
steps that must not be re-implemented (or forgotten) per document type:

1. validate the caller's permissions for that document type,
2. prepare the document data via the type's loader (which loads the source
   record and enforces tenant/facility ownership),
3. re-validate tenant/facility on what the loader returned (defense in
   depth - a loader that forgets its check is still caught here),
4. resolve the facility's template (P7-B02) and paper size,
5. render to PDF and write an audit event.

Receipts and consents are HTML/CSS (Jinja2) rendered by Playwright (P7-B03).
The lab report keeps its own fpdf2 layout.

Adding a document type = one `DocumentSpec` entry in the registry below.
"""
import re
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, ForbiddenError, NotFoundError
from app.core.permissions import ensure_same_facility, ensure_same_tenant
from app.modules.audit import service as audit_service
from app.modules.audit.models import AuditLog
from app.modules.audit.schemas import AuditLogOut
from app.modules.auth.models import User
from app.modules.billing.models import Receipt
from app.modules.billing.schemas import ReceiptOut
from app.modules.documents import catalog, codes
from app.modules.documents.base import (
    DocumentContext,
    DocumentSpec,
    DocumentSummary,
    PreparedDocument,
    get_facility as _get_facility,
    patient_name as _patient_name,
    render_html_pdf as _render_html_pdf_ctx,
)
from app.modules.documents.layout import PAPER_SIZES
from app.modules.documents.schemas import DocumentTypeOut
from app.modules.documents.templates import resolve_template
from app.modules.ipd.models import Admission, Consent
from app.modules.lab import service as lab_service
from app.modules.lab.models import LabOrder
from app.modules.lab.report_pdf import build_lab_report_pdf
from app.modules.patients.models import Patient


# --- LAB_REPORT -------------------------------------------------------------


async def _load_lab_report(db: AsyncSession, resource_id: uuid.UUID, user: User) -> PreparedDocument:
    order = await db.get(LabOrder, resource_id)
    if order is None:
        raise NotFoundError("Lab order not found.")
    ensure_same_tenant(order.tenant_id, user)
    ensure_same_facility(order.facility_id, user)
    # Also enforces the APPROVED/FINALIZED gate on the report itself.
    report = await lab_service.get_lab_report(db, user, resource_id)
    return PreparedDocument(order.tenant_id, order.facility_id, report.order_number, report)


async def _render_lab_report(db: AsyncSession, doc: PreparedDocument, ctx: DocumentContext) -> bytes:
    report = doc.data
    verify_url = (
        f"{ctx.base_url}api/v1/lab/verify-doc?id={report.lab_order_id}&sig={report.report_qr_token}"
        if report.report_qr_token
        else None
    )
    return build_lab_report_pdf(report, verify_url=verify_url)


# --- RECEIPT ----------------------------------------------------------------


async def _load_receipt(db: AsyncSession, resource_id: uuid.UUID, user: User) -> PreparedDocument:
    receipt = await db.get(Receipt, resource_id)
    if receipt is None:
        raise NotFoundError("Receipt not found.")
    ensure_same_tenant(receipt.tenant_id, user)
    ensure_same_facility(receipt.facility_id, user)
    patient = await db.get(Patient, receipt.patient_id)
    if patient is None:
        raise NotFoundError("Patient not found.")
    data = {"receipt": ReceiptOut.model_validate(receipt), "patient": patient}
    return PreparedDocument(receipt.tenant_id, receipt.facility_id, receipt.receipt_number, data)


async def _summarize_receipt(db: AsyncSession, receipt_id: uuid.UUID) -> DocumentSummary | None:
    receipt = await db.get(Receipt, receipt_id)
    if receipt is None:
        return None
    facility = await _get_facility(db, receipt.facility_id)
    return DocumentSummary(
        receipt.receipt_number, facility.name, receipt.issued_at, receipt.tenant_id, receipt.facility_id
    )


async def _render_receipt(db: AsyncSession, doc: PreparedDocument, ctx: DocumentContext) -> bytes:
    receipt: ReceiptOut = doc.data["receipt"]
    patient: Patient = doc.data["patient"]
    facility = await _get_facility(db, doc.facility_id)
    return await _render_html_pdf_ctx(
        "receipt.html",
        ctx,
        facility=facility,
        title=f"{receipt.receipt_type.title()} Receipt",
        default_signatures=["Cashier"],
        receipt=receipt,
        patient=patient,
        patient_name=_patient_name(patient),
        issued_at=receipt.issued_at.strftime("%d %b %Y %H:%M"),
    )


# --- IPD_CONSENT ------------------------------------------------------------


async def _load_consent(db: AsyncSession, resource_id: uuid.UUID, user: User) -> PreparedDocument:
    consent = await db.get(Consent, resource_id)
    if consent is None:
        raise NotFoundError("Consent not found.")
    ensure_same_tenant(consent.tenant_id, user)
    ensure_same_facility(consent.facility_id, user)
    admission = await db.get(Admission, consent.admission_id)
    if admission is None:
        raise NotFoundError("Admission not found.")
    patient = await db.get(Patient, admission.patient_id)
    if patient is None:
        raise NotFoundError("Patient not found.")
    data = {"consent": consent, "admission": admission, "patient": patient}
    return PreparedDocument(
        consent.tenant_id, consent.facility_id, f"consent-{admission.admission_number}", data,
        reference=_consent_reference(consent),
    )


def _consent_reference(consent: Consent) -> str:
    return f"CNS-{str(consent.id)[:8].upper()}"


async def _summarize_consent(db: AsyncSession, consent_id: uuid.UUID) -> DocumentSummary | None:
    consent = await db.get(Consent, consent_id)
    if consent is None:
        return None
    facility = await _get_facility(db, consent.facility_id)
    return DocumentSummary(
        _consent_reference(consent), facility.name, consent.recorded_at, consent.tenant_id, consent.facility_id
    )


async def _render_consent(db: AsyncSession, doc: PreparedDocument, ctx: DocumentContext) -> bytes:
    consent: Consent = doc.data["consent"]
    admission: Admission = doc.data["admission"]
    patient: Patient = doc.data["patient"]
    facility = await _get_facility(db, doc.facility_id)
    kind = consent.consent_type.replace("_", " ")
    return await _render_html_pdf_ctx(
        "consent.html",
        ctx,
        facility=facility,
        title=f"Consent - {kind.title()}",
        default_signatures=["Patient / Guardian", "Doctor", "Witness"],
        consent=consent,
        admission=admission,
        patient=patient,
        patient_name=_patient_name(patient),
        kind=kind,
        recorded_at=consent.recorded_at.strftime("%d %b %Y %H:%M"),
    )


_REGISTRY: dict[str, DocumentSpec] = {
    spec.code: spec
    for spec in (
        DocumentSpec("LAB_REPORT", "Laboratory Report", ("lab.view",), "lab_order", _load_lab_report, _render_lab_report),
        DocumentSpec(
            "RECEIPT", "Payment Receipt", ("billing.view",), "receipt", _load_receipt, _render_receipt, templatable=True,
            secure_codes=True, summarize=_summarize_receipt,
        ),
        DocumentSpec(
            "IPD_CONSENT", "IPD Consent Form", ("ipd.view",), "ipd_consent", _load_consent, _render_consent,
            templatable=True, secure_codes=True, summarize=_summarize_consent,
        ),
        *catalog.SPECS,
    )
}


def supports_templates(doc_type: str) -> bool:
    spec = _REGISTRY.get(doc_type.upper())
    return spec is not None and spec.templatable


# Every document needs the generic print permission IN ADDITION to the module
# permission for what it contains (P7-B06): seeing a record in its module is
# not the same as being allowed to produce a printable copy of it.
PRINT_PERMISSION = "documents.print"


def _required_permissions(spec: DocumentSpec) -> set[str]:
    return {PRINT_PERMISSION, *spec.permissions}


def safe_filename(name: str) -> str:
    """Download names come from record numbers; keep them header-safe."""
    cleaned = re.sub(r"\.{2,}", ".", re.sub(r"[^A-Za-z0-9._-]+", "_", name)).strip("._")
    return cleaned[:80] or "document"


def _user_permissions(user: User) -> set[str]:
    return {permission.code for permission in user.role.permissions}


def list_document_types(user: User) -> list[DocumentTypeOut]:
    """Document types the caller is allowed to generate."""
    held = _user_permissions(user)
    return [
        DocumentTypeOut(
            code=s.code,
            title=s.title,
            required_permissions=list(s.permissions),
            supports_templates=s.templatable,
        )
        for s in _REGISTRY.values()
        if _required_permissions(s) <= held
    ]


@dataclass
class GeneratedDocument:
    content: bytes
    filename: str
    media_type: str = "application/pdf"


async def _audit_outcome(
    db: AsyncSession,
    action: str,
    spec: DocumentSpec,
    resource_id: uuid.UUID,
    actor: tuple[uuid.UUID, uuid.UUID, uuid.UUID],
    after: dict,
) -> None:
    actor_user_id, tenant_id, facility_id = actor
    await audit_service.record_event(
        db,
        action=action,
        resource_type=spec.resource_type,
        resource_id=resource_id,
        after={"document_type": spec.code, **after},
        actor_user_id=actor_user_id,
        tenant_id=tenant_id,
        facility_id=facility_id,
        commit=True,
    )


async def generate_document(
    db: AsyncSession,
    doc_type: str,
    resource_id: uuid.UUID,
    user: User,
    context: DocumentContext | None = None,
    template_version: int | None = None,
    paper_size: str | None = None,
    custom_size_mm: tuple[float, float] | None = None,
    access: dict | None = None,
) -> GeneratedDocument:
    """Authorize, build and audit one document.

    `access` is request metadata worth keeping on every audit event (how it
    was delivered, the client address).
    """
    access = access or {}
    spec = _REGISTRY.get(doc_type.upper())
    if spec is None:
        raise AppError(f"Unknown document type '{doc_type}'.", code="UNKNOWN_DOCUMENT_TYPE", status_code=404)

    # Captured now: after a rollback the ORM user object is expired and cannot
    # be read in async code, but the failure audit below still needs these.
    actor = (user.id, user.tenant_id, user.facility_id)

    # 1. Authorization comes before anything is loaded or rendered.
    missing = sorted(_required_permissions(spec) - _user_permissions(user))
    if missing:
        await _audit_outcome(
            db, "document.access_denied", spec, resource_id, actor, {"missing_permissions": missing, **access}
        )
        raise ForbiddenError("You do not have permission to generate this document.")

    try:
        # 2. The record must belong to the caller's tenant and facility
        #    (loaders check; re-checked here in case one forgets).
        prepared = await spec.load(db, resource_id, user)
        ensure_same_tenant(prepared.tenant_id, user)
        ensure_same_facility(prepared.facility_id, user)

        context = context or DocumentContext()
        context.default_settings = spec.default_settings
        context.doc_type = spec.code
        context.resource_id = resource_id
        context.reference = prepared.ref
        context.secure_codes = spec.secure_codes
        context.verify_base_url = get_settings().public_base_url or context.base_url
        if (template_version is not None or paper_size is not None) and not spec.templatable:
            raise AppError(
                f"{spec.code} uses a fixed layout; template versions and paper sizes do not apply.",
                code="TEMPLATE_NOT_SUPPORTED",
            )
        if paper_size is not None:
            if paper_size not in PAPER_SIZES:
                raise AppError(f"Unknown paper size '{paper_size}'.", code="INVALID_PAPER_SIZE")
            context.paper_size = paper_size
            if custom_size_mm:
                context.custom_width_mm, context.custom_height_mm = custom_size_mm
        if spec.templatable:
            context.template = await resolve_template(db, user, spec.code, template_version)
            context.settings().page()  # reject a bad paper size before doing any work

        content = await spec.render(db, prepared, context)
    except Exception as exc:
        # Includes cross-facility attempts (reported as 404 to the caller so
        # existence is not leaked, but recorded here for the audit trail).
        await db.rollback()
        await _audit_outcome(
            db,
            "document.generation_failed",
            spec,
            resource_id,
            actor,
            {"error_code": getattr(exc, "code", "INTERNAL_ERROR"), **access},
        )
        raise

    await _audit_outcome(
        db,
        "document.generated",
        spec,
        resource_id,
        actor,
        {
            "filename": prepared.filename,
            "reference": prepared.ref if spec.secure_codes else None,
            # Records which layout produced this document so it can be reproduced.
            "template_id": str(context.template.template_id) if context.template else None,
            "template_version": context.template.version_number if context.template else None,
            "paper_size": context.settings().paper_size if spec.templatable else "A4",
            "custom_size_mm": list(custom_size_mm) if custom_size_mm and paper_size == "CUSTOM" else None,
            "size_bytes": len(content),
            **access,
        },
    )
    return GeneratedDocument(content=content, filename=f"{safe_filename(prepared.filename)}.pdf")


async def list_document_events(
    db: AsyncSession, doc_type: str, resource_id: uuid.UUID, user: User
) -> list[AuditLogOut]:
    """Who generated, was denied, or failed to generate this document."""
    spec = _REGISTRY.get(doc_type.upper())
    if spec is None:
        raise AppError(f"Unknown document type '{doc_type}'.", code="UNKNOWN_DOCUMENT_TYPE", status_code=404)
    result = await db.execute(
        select(AuditLog)
        .where(
            AuditLog.tenant_id == user.tenant_id,
            AuditLog.facility_id == user.facility_id,
            AuditLog.resource_type == spec.resource_type,
            AuditLog.resource_id == str(resource_id),
            AuditLog.action.like("document.%"),
        )
        .order_by(AuditLog.created_at.desc())
        .limit(200)
    )
    return [AuditLogOut.model_validate(row) for row in result.scalars().all()]


@dataclass
class VerificationResult:
    valid: bool
    document_type: str | None = None
    reference: str | None = None
    facility_name: str | None = None
    issued_at: str | None = None


async def verify_document(db: AsyncSession, doc_type: str, resource_id: uuid.UUID, signature: str) -> VerificationResult:
    """Public (unauthenticated) check of a printed document QR.

    Reveals only the document type, its reference number, the facility and
    the issue date - no patient data. An unknown type, an unknown id and a
    wrong signature all return the same "not valid" answer, so the endpoint
    cannot be used to probe which ids exist.
    """
    spec = _REGISTRY.get(doc_type.upper())
    if spec is None or spec.summarize is None or not spec.secure_codes:
        return VerificationResult(valid=False)
    summary = await spec.summarize(db, resource_id)
    if summary is None or not codes.verify_signature(spec.code, resource_id, summary.reference, signature):
        return VerificationResult(valid=False)

    await audit_service.record_event(
        db,
        action="document.verified",
        resource_type=spec.resource_type,
        resource_id=resource_id,
        after={"document_type": spec.code, "reference": summary.reference},
        tenant_id=summary.tenant_id,
        facility_id=summary.facility_id,
        commit=True,
    )
    return VerificationResult(
        valid=True,
        document_type=spec.code,
        reference=summary.reference,
        facility_name=summary.facility_name,
        issued_at=summary.issued_at.isoformat() if summary.issued_at else None,
    )
