"""Shared building blocks for document specs (engine types and render helpers)."""
import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any, Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.auth.models import User
from app.modules.documents import codes
from app.modules.documents.html_render import render_html
from app.modules.documents.layout import RenderSettings
from app.modules.documents.playwright_pdf import render_pdf
from app.modules.documents.templates import ResolvedTemplate
from app.modules.facilities.models import Facility
from app.modules.patients.models import Patient


@dataclass
class PreparedDocument:
    """Data ready to render, plus the ownership keys the engine re-checks."""

    tenant_id: uuid.UUID
    facility_id: uuid.UUID
    filename: str
    data: Any
    # The human-readable number printed on the document and encoded in its
    # barcode/QR (receipt no., invoice no., ...). Defaults to the filename.
    reference: str | None = None

    @property
    def ref(self) -> str:
        return self.reference or self.filename


@dataclass
class DocumentContext:
    """Request-derived values a renderer may need (e.g. absolute verify URLs)."""

    base_url: str = ""
    # Set by the engine for templatable document types; None = default layout.
    template: ResolvedTemplate | None = None
    # What the document type looks like when no template applies.
    default_settings: RenderSettings = field(default_factory=RenderSettings)
    # Caller's paper-size choice at print time; beats the template's.
    paper_size: str | None = None
    custom_width_mm: float | None = None
    custom_height_mm: float | None = None
    # Secure-code inputs, set by the engine (P7-B05).
    doc_type: str = ""
    resource_id: uuid.UUID | None = None
    reference: str | None = None
    secure_codes: bool = False
    verify_base_url: str = ""

    def settings(self) -> RenderSettings:
        base = self.template.settings if self.template else self.default_settings
        if not self.paper_size:
            return base
        return replace(
            base,
            paper_size=self.paper_size,
            custom_width_mm=self.custom_width_mm,
            custom_height_mm=self.custom_height_mm,
        )


@dataclass(frozen=True)
class DocumentSummary:
    """The minimum a public verification may reveal about a document."""

    reference: str
    facility_name: str
    issued_at: datetime | None
    tenant_id: uuid.UUID
    facility_id: uuid.UUID


Summarizer = Callable[[AsyncSession, uuid.UUID], Awaitable["DocumentSummary | None"]]
Loader = Callable[[AsyncSession, uuid.UUID, User], Awaitable[PreparedDocument]]
Renderer = Callable[[AsyncSession, PreparedDocument, DocumentContext], Awaitable[bytes]]


@dataclass(frozen=True)
class DocumentSpec:
    code: str
    title: str
    permissions: tuple[str, ...]
    resource_type: str
    load: Loader
    render: Renderer
    # Whether the renderer honours a facility template and a chosen paper
    # size. The lab report PDF has its own fixed A4 layout, so it does not.
    templatable: bool = False
    # Layout used when the facility has no active template for this type.
    default_settings: RenderSettings = field(default_factory=RenderSettings)
    # P7-B05: print a signed verification QR and a reference barcode, and the
    # lookup that lets the public verify endpoint confirm the document.
    secure_codes: bool = False
    summarize: Summarizer | None = None


async def get_facility(db: AsyncSession, facility_id: uuid.UUID) -> Facility:
    facility = await db.get(Facility, facility_id)
    if facility is None:
        raise NotFoundError("Facility not found.")
    return facility


async def get_patient(db: AsyncSession, patient_id: uuid.UUID) -> Patient:
    patient = await db.get(Patient, patient_id)
    if patient is None:
        raise NotFoundError("Patient not found.")
    return patient


def patient_name(patient: Patient) -> str:
    return " ".join(p for p in (patient.title, patient.first_name, patient.middle_name, patient.last_name) if p)


def fmt_datetime(value) -> str:
    return value.strftime("%d %b %Y %H:%M") if value else "-"


async def render_html_pdf(template_name: str, ctx: DocumentContext, **context) -> bytes:
    settings = ctx.settings()
    page = settings.page()  # validates the paper size / custom dimensions
    if ctx.secure_codes and ctx.resource_id is not None and ctx.reference:
        # Validated and self-checked here; a bad reference stops the render
        # instead of printing a code that can never verify.
        reference = codes.validate_reference(ctx.reference)
        verify_url = codes.build_verify_url(ctx.verify_base_url, ctx.doc_type, ctx.resource_id, reference)
        context.setdefault("secure_reference", reference)
        context.setdefault("secure_barcode", codes.code128_svg(reference))
        context.setdefault("secure_qr", codes.qr_data_uri(verify_url, box_size=3, border=1))
    html_source = render_html(template_name, settings=settings, page=page, **context)
    return await render_pdf(html_source, page=page, footer_text=settings.footer_text)
