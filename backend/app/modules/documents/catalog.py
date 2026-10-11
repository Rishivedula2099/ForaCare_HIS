"""P7-F04/P7-B04: document types for the OPD, IPD (admission, discharge),
billing (invoice) and patient-label modules.

Each type is a loader (fetch + tenant/facility check) and a renderer that
feeds an HTML template. Keyed by the id the module's own screens already
have: encounter id for OPD documents, admission id for IPD documents.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.permissions import ensure_same_facility, ensure_same_tenant
from app.modules.auth.models import User
from app.modules.billing.models import Invoice, InvoiceItem
from app.modules.departments.models import Department
from app.modules.doctors.models import Doctor
from app.modules.documents.base import (
    DocumentContext,
    DocumentSpec,
    DocumentSummary,
    PreparedDocument,
    fmt_datetime,
    get_facility,
    get_patient,
    patient_name,
    render_html_pdf,
)
from app.modules.documents.codes import qr_data_uri
from app.modules.documents.layout import CUSTOM, RenderSettings
from app.modules.ipd.models import Admission, Discharge
from app.modules.opd.models import Consultation, OPDEncounter, Prescription, PrescriptionItem
from app.modules.patients.models import Patient


async def _summary(db: AsyncSession, record, reference: str, issued_at) -> DocumentSummary:
    facility = await get_facility(db, record.facility_id)
    return DocumentSummary(reference, facility.name, issued_at, record.tenant_id, record.facility_id)


def _own(record, user: User) -> None:
    ensure_same_tenant(record.tenant_id, user)
    ensure_same_facility(record.facility_id, user)


async def _name_of(db: AsyncSession, model, record_id: uuid.UUID | None, attr: str) -> str | None:
    if record_id is None:
        return None
    row = await db.get(model, record_id)
    return getattr(row, attr) if row else None


async def _get_encounter(db: AsyncSession, encounter_id: uuid.UUID, user: User) -> OPDEncounter:
    encounter = await db.get(OPDEncounter, encounter_id)
    if encounter is None:
        raise NotFoundError("Encounter not found.")
    _own(encounter, user)
    return encounter


async def _get_admission(db: AsyncSession, admission_id: uuid.UUID, user: User) -> Admission:
    admission = await db.get(Admission, admission_id)
    if admission is None:
        raise NotFoundError("Admission not found.")
    _own(admission, user)
    return admission


# --- OPD_TOKEN --------------------------------------------------------------


async def _load_opd_token(db: AsyncSession, encounter_id: uuid.UUID, user: User) -> PreparedDocument:
    encounter = await _get_encounter(db, encounter_id, user)
    token = encounter.token
    if token is None:
        raise NotFoundError("This encounter has no queue token.")
    data = {
        "encounter": encounter,
        "token": token,
        "patient": await get_patient(db, encounter.patient_id),
        "doctor_name": await _name_of(db, Doctor, encounter.doctor_id, "full_name"),
        "department_name": await _name_of(db, Department, encounter.department_id, "name"),
    }
    return PreparedDocument(encounter.tenant_id, encounter.facility_id, f"token-{token.token_number}", data)


async def _render_opd_token(db: AsyncSession, doc: PreparedDocument, ctx: DocumentContext) -> bytes:
    d = doc.data
    return await render_html_pdf(
        "opd_token.html",
        ctx,
        facility=await get_facility(db, doc.facility_id),
        title="OPD Token",
        default_signatures=[],
        patient_name=patient_name(d["patient"]),
        **d,
    )


# --- OPD_PRESCRIPTION -------------------------------------------------------


async def _load_opd_prescription(db: AsyncSession, encounter_id: uuid.UUID, user: User) -> PreparedDocument:
    encounter = await _get_encounter(db, encounter_id, user)
    consultation = (
        await db.execute(select(Consultation).where(Consultation.encounter_id == encounter.id))
    ).scalar_one_or_none()
    prescription = (
        await db.execute(select(Prescription).where(Prescription.consultation_id == consultation.id))
    ).scalar_one_or_none() if consultation else None
    if consultation is None or prescription is None:
        raise NotFoundError("No prescription has been written for this encounter.")
    _own(prescription, user)
    items = (
        await db.execute(
            select(PrescriptionItem)
            .where(PrescriptionItem.prescription_id == prescription.id)
            .order_by(PrescriptionItem.created_at)
        )
    ).scalars().all()
    data = {
        "encounter": encounter,
        "consultation": consultation,
        "items": items,
        "patient": await get_patient(db, encounter.patient_id),
        "doctor_name": await _name_of(db, Doctor, prescription.doctor_id, "full_name"),
        "created_at": fmt_datetime(prescription.created_at),
    }
    return PreparedDocument(
        encounter.tenant_id, encounter.facility_id, f"rx-{encounter.encounter_number}", data,
        reference=encounter.encounter_number,
    )


async def _summarize_prescription(db: AsyncSession, encounter_id: uuid.UUID) -> DocumentSummary | None:
    encounter = await db.get(OPDEncounter, encounter_id)
    if encounter is None:
        return None
    consultation = (
        await db.execute(select(Consultation).where(Consultation.encounter_id == encounter.id))
    ).scalar_one_or_none()
    prescription = (
        await db.execute(select(Prescription).where(Prescription.consultation_id == consultation.id))
    ).scalar_one_or_none() if consultation else None
    if prescription is None:
        return None
    return await _summary(db, encounter, encounter.encounter_number, prescription.created_at)


async def _render_opd_prescription(db: AsyncSession, doc: PreparedDocument, ctx: DocumentContext) -> bytes:
    d = doc.data
    return await render_html_pdf(
        "opd_prescription.html",
        ctx,
        facility=await get_facility(db, doc.facility_id),
        title="Prescription",
        default_signatures=["Doctor signature"],
        patient_name=patient_name(d["patient"]),
        **d,
    )


# --- IPD_ADMISSION_FORM -----------------------------------------------------


async def _load_admission_form(db: AsyncSession, admission_id: uuid.UUID, user: User) -> PreparedDocument:
    admission = await _get_admission(db, admission_id, user)
    data = {
        "admission": admission,
        "patient": await get_patient(db, admission.patient_id),
        "doctor_name": await _name_of(db, Doctor, admission.admitting_doctor_id, "full_name"),
        "department_name": await _name_of(db, Department, admission.department_id, "name"),
        "admitted_at": fmt_datetime(admission.admitted_at),
    }
    return PreparedDocument(
        admission.tenant_id, admission.facility_id, f"admission-{admission.admission_number}", data,
        reference=admission.admission_number,
    )


async def _summarize_admission_form(db: AsyncSession, admission_id: uuid.UUID) -> DocumentSummary | None:
    admission = await db.get(Admission, admission_id)
    if admission is None:
        return None
    return await _summary(db, admission, admission.admission_number, admission.admitted_at)


async def _render_admission_form(db: AsyncSession, doc: PreparedDocument, ctx: DocumentContext) -> bytes:
    d = doc.data
    return await render_html_pdf(
        "ipd_admission.html",
        ctx,
        facility=await get_facility(db, doc.facility_id),
        title="Admission Form",
        default_signatures=["Patient / Guardian", "Admitting doctor"],
        patient_name=patient_name(d["patient"]),
        **d,
    )


# --- IPD_DISCHARGE_SUMMARY --------------------------------------------------


async def _load_discharge_summary(db: AsyncSession, admission_id: uuid.UUID, user: User) -> PreparedDocument:
    admission = await _get_admission(db, admission_id, user)
    discharge = (
        await db.execute(select(Discharge).where(Discharge.admission_id == admission.id))
    ).scalar_one_or_none()
    if discharge is None:
        raise NotFoundError("This patient has not been discharged yet.")
    _own(discharge, user)
    data = {
        "admission": admission,
        "discharge": discharge,
        "patient": await get_patient(db, admission.patient_id),
        "doctor_name": await _name_of(db, Doctor, admission.admitting_doctor_id, "full_name"),
        "department_name": await _name_of(db, Department, admission.department_id, "name"),
        "admitted_at": fmt_datetime(admission.admitted_at),
        "discharged_at": fmt_datetime(discharge.discharged_at),
    }
    return PreparedDocument(
        admission.tenant_id, admission.facility_id, f"discharge-{admission.admission_number}", data,
        reference=admission.admission_number,
    )


async def _summarize_discharge(db: AsyncSession, admission_id: uuid.UUID) -> DocumentSummary | None:
    admission = await db.get(Admission, admission_id)
    if admission is None:
        return None
    discharge = (
        await db.execute(select(Discharge).where(Discharge.admission_id == admission.id))
    ).scalar_one_or_none()
    if discharge is None:
        return None
    return await _summary(db, admission, admission.admission_number, discharge.discharged_at)


async def _render_discharge_summary(db: AsyncSession, doc: PreparedDocument, ctx: DocumentContext) -> bytes:
    d = doc.data
    return await render_html_pdf(
        "ipd_discharge.html",
        ctx,
        facility=await get_facility(db, doc.facility_id),
        title="Discharge Summary",
        default_signatures=["Patient / Guardian", "Treating doctor"],
        patient_name=patient_name(d["patient"]),
        **d,
    )


# --- INVOICE ----------------------------------------------------------------


async def _load_invoice(db: AsyncSession, invoice_id: uuid.UUID, user: User) -> PreparedDocument:
    invoice = await db.get(Invoice, invoice_id)
    if invoice is None:
        raise NotFoundError("Invoice not found.")
    _own(invoice, user)
    items = (
        await db.execute(
            select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id).order_by(InvoiceItem.created_at)
        )
    ).scalars().all()
    data = {
        "invoice": invoice,
        "items": items,
        "patient": await get_patient(db, invoice.patient_id),
        "invoice_date": fmt_datetime(invoice.invoice_date),
    }
    return PreparedDocument(invoice.tenant_id, invoice.facility_id, invoice.invoice_number, data)


async def _summarize_invoice(db: AsyncSession, invoice_id: uuid.UUID) -> DocumentSummary | None:
    invoice = await db.get(Invoice, invoice_id)
    if invoice is None:
        return None
    return await _summary(db, invoice, invoice.invoice_number, invoice.invoice_date)


async def _render_invoice(db: AsyncSession, doc: PreparedDocument, ctx: DocumentContext) -> bytes:
    d = doc.data
    return await render_html_pdf(
        "invoice.html",
        ctx,
        facility=await get_facility(db, doc.facility_id),
        title="Invoice",
        default_signatures=["Cashier"],
        patient_name=patient_name(d["patient"]),
        **d,
    )


# --- PATIENT_LABEL ----------------------------------------------------------


def _qr_data_uri(text: str) -> str:
    return qr_data_uri(text)


async def _load_patient_label(db: AsyncSession, patient_id: uuid.UUID, user: User) -> PreparedDocument:
    patient: Patient = await get_patient(db, patient_id)
    _own(patient, user)
    return PreparedDocument(patient.tenant_id, patient.facility_id, f"label-{patient.mrn}", {"patient": patient})


async def _render_patient_label(db: AsyncSession, doc: PreparedDocument, ctx: DocumentContext) -> bytes:
    patient: Patient = doc.data["patient"]
    return await render_html_pdf(
        "patient_label.html",
        ctx,
        facility=await get_facility(db, doc.facility_id),
        title="Patient Label",
        hide_letterhead=True,
        patient=patient,
        patient_name=patient_name(patient),
        qr=_qr_data_uri(patient.mrn),
    )


_THERMAL_80 = RenderSettings(paper_size="THERMAL_80")
_A5 = RenderSettings(paper_size="A5")
_LABEL_50X25 = RenderSettings(paper_size=CUSTOM, custom_width_mm=50, custom_height_mm=25)

SPECS: tuple[DocumentSpec, ...] = (
    DocumentSpec(
        "OPD_TOKEN", "OPD Token", ("opd.view",), "opd_encounter",
        _load_opd_token, _render_opd_token, templatable=True, default_settings=_THERMAL_80,
    ),
    DocumentSpec(
        "OPD_PRESCRIPTION", "Prescription", ("prescriptions.view",), "opd_prescription",
        _load_opd_prescription, _render_opd_prescription, templatable=True, default_settings=_A5,
        secure_codes=True, summarize=_summarize_prescription,
    ),
    DocumentSpec(
        "IPD_ADMISSION_FORM", "IPD Admission Form", ("ipd.view",), "ipd_admission",
        _load_admission_form, _render_admission_form, templatable=True,
        secure_codes=True, summarize=_summarize_admission_form,
    ),
    DocumentSpec(
        "IPD_DISCHARGE_SUMMARY", "Discharge Summary", ("ipd.view",), "ipd_discharge",
        _load_discharge_summary, _render_discharge_summary, templatable=True,
        secure_codes=True, summarize=_summarize_discharge,
    ),
    DocumentSpec(
        "INVOICE", "Invoice", ("billing.view",), "billing_invoice",
        _load_invoice, _render_invoice, templatable=True,
        secure_codes=True, summarize=_summarize_invoice,
    ),
    DocumentSpec(
        "PATIENT_LABEL", "Patient Label", ("patients.view",), "patient",
        _load_patient_label, _render_patient_label, templatable=True, default_settings=_LABEL_50X25,
    ),
)
