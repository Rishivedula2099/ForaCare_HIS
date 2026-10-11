"""P7-B02: document template versioning.

A `DocumentTemplate` is a mutable pointer; every layout change is a new,
immutable `DocumentTemplateVersion`. That gives historical reproducibility:
the engine records the template id + version on every generated document's
audit event, and `resolve_template(..., version=N)` re-renders with exactly
version N even after V2/V3 exist or the template was deactivated.
(Reproducibility covers the *layout*; the document's data is read live from
its source record, as it is for every document.)
"""
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError, ConflictError, NotFoundError
from app.core.permissions import ensure_same_facility, ensure_same_tenant
from app.modules.audit import service as audit_service
from app.modules.auth.models import User
from app.modules.documents.models import DocumentTemplate, DocumentTemplateVersion
from app.modules.documents.layout import RenderSettings
from app.modules.documents.schemas import (
    TemplateContent,
    TemplateCreateRequest,
    TemplateDetailOut,
    TemplateOut,
    TemplateUpdateRequest,
    TemplateVersionCreateRequest,
    TemplateVersionOut,
)


@dataclass
class ResolvedTemplate:
    template_id: uuid.UUID
    version_number: int
    settings: RenderSettings


def _version(template: DocumentTemplate, number: int) -> DocumentTemplateVersion:
    for version in template.versions:
        if version.version_number == number:
            return version
    raise NotFoundError(f"Template version {number} not found.")


def _to_out(template: DocumentTemplate) -> TemplateOut:
    return TemplateOut(
        id=template.id,
        facility_id=template.facility_id,
        document_type=template.document_type,
        name=template.name,
        is_active=template.is_active,
        active_version_number=template.active_version_number,
        paper_size=_version(template, template.active_version_number).paper_size,
        latest_version_number=max(v.version_number for v in template.versions),
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def _to_detail(template: DocumentTemplate) -> TemplateDetailOut:
    return TemplateDetailOut(
        **_to_out(template).model_dump(),
        versions=[TemplateVersionOut.model_validate(v) for v in reversed(template.versions)],
    )


async def _get_or_404(db: AsyncSession, template_id: uuid.UUID, user: User, *, for_update: bool = False):
    stmt = select(DocumentTemplate).where(DocumentTemplate.id == template_id)
    if for_update:
        # `of=` keeps the lock on the template row; versions are loaded by a
        # separate selectin query.
        stmt = stmt.with_for_update(of=DocumentTemplate)
    template = (await db.execute(stmt)).scalar_one_or_none()
    if template is None:
        raise NotFoundError("Template not found.")
    ensure_same_tenant(template.tenant_id, user)
    ensure_same_facility(template.facility_id, user)
    return template


def _audit_after(template: DocumentTemplate, **extra) -> dict:
    return {
        "document_type": template.document_type,
        "active_version_number": template.active_version_number,
        "is_active": template.is_active,
        **extra,
    }


async def list_templates(db: AsyncSession, user: User, document_type: str | None = None) -> list[TemplateOut]:
    stmt = select(DocumentTemplate).where(
        DocumentTemplate.tenant_id == user.tenant_id, DocumentTemplate.facility_id == user.facility_id
    )
    if document_type:
        stmt = stmt.where(DocumentTemplate.document_type == document_type.upper())
    result = await db.execute(stmt.order_by(DocumentTemplate.document_type))
    return [_to_out(t) for t in result.scalars().all()]


async def get_template(db: AsyncSession, template_id: uuid.UUID, user: User) -> TemplateDetailOut:
    return _to_detail(await _get_or_404(db, template_id, user))


async def create_template(db: AsyncSession, payload: TemplateCreateRequest, user: User) -> TemplateDetailOut:
    from app.modules.documents.service import supports_templates  # avoids a circular import

    document_type = payload.document_type.upper()
    if not supports_templates(document_type):
        raise AppError(
            f"Document type '{payload.document_type}' does not support templates.", code="TEMPLATE_NOT_SUPPORTED"
        )

    template = DocumentTemplate(
        tenant_id=user.tenant_id,
        facility_id=user.facility_id,
        document_type=document_type,
        name=payload.name,
        is_active=True,
        active_version_number=1,
        created_by=user.id,
    )
    template.versions = [
        DocumentTemplateVersion(
            version_number=1,
            paper_size=payload.paper_size,
            content=payload.content.model_dump(),
            change_note=payload.change_note,
            created_by=user.id,
        )
    ]
    db.add(template)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise ConflictError(f"This facility already has a {document_type} template; add a new version instead.")

    await audit_service.record_event(
        db,
        action="document_template.created",
        resource_type="document_template",
        resource_id=template.id,
        after=_audit_after(template, paper_size=payload.paper_size),
        commit=False,
    )
    await db.commit()
    await db.refresh(template)
    return _to_detail(template)


async def create_version(
    db: AsyncSession, template_id: uuid.UUID, payload: TemplateVersionCreateRequest, user: User
) -> TemplateDetailOut:
    template = await _get_or_404(db, template_id, user, for_update=True)
    next_number = max(v.version_number for v in template.versions) + 1
    before = _audit_after(template)
    # A new version goes live immediately; older versions stay reproducible.
    template.versions.append(
        DocumentTemplateVersion(
            version_number=next_number,
            paper_size=payload.paper_size,
            content=payload.content.model_dump(),
            change_note=payload.change_note,
            created_by=user.id,
        )
    )
    template.active_version_number = next_number
    await db.flush()

    await audit_service.record_event(
        db,
        action="document_template.version_created",
        resource_type="document_template",
        resource_id=template.id,
        before=before,
        after=_audit_after(template, paper_size=payload.paper_size),
        commit=False,
    )
    await db.commit()
    await db.refresh(template)
    return _to_detail(template)


async def activate_version(
    db: AsyncSession, template_id: uuid.UUID, version_number: int, user: User
) -> TemplateDetailOut:
    """Makes an existing version the live one (e.g. rolling V3 back to V2)."""
    template = await _get_or_404(db, template_id, user, for_update=True)
    _version(template, version_number)  # 404 if it does not exist
    before = _audit_after(template)
    template.active_version_number = version_number
    await audit_service.record_event(
        db,
        action="document_template.version_activated",
        resource_type="document_template",
        resource_id=template.id,
        before=before,
        after=_audit_after(template),
        commit=False,
    )
    await db.commit()
    await db.refresh(template)
    return _to_detail(template)


async def update_template(
    db: AsyncSession, template_id: uuid.UUID, payload: TemplateUpdateRequest, user: User
) -> TemplateDetailOut:
    template = await _get_or_404(db, template_id, user, for_update=True)
    before = _audit_after(template, name=template.name)
    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(template, key, value)
    await audit_service.record_event(
        db,
        action="document_template.updated",
        resource_type="document_template",
        resource_id=template.id,
        before=before,
        after=_audit_after(template, name=template.name),
        commit=False,
    )
    await db.commit()
    await db.refresh(template)
    return _to_detail(template)


async def resolve_template(
    db: AsyncSession, user: User, document_type: str, version: int | None = None
) -> ResolvedTemplate | None:
    """The template layout to render with, or None for the built-in default.

    No `version` -> the facility's active version, only if the template is
    active. An explicit `version` always wins, even over an inactive
    template, because it is how a historical document is reproduced.
    """
    template = (
        await db.execute(
            select(DocumentTemplate).where(
                DocumentTemplate.tenant_id == user.tenant_id,
                DocumentTemplate.facility_id == user.facility_id,
                DocumentTemplate.document_type == document_type,
            )
        )
    ).scalar_one_or_none()

    if version is None:
        if template is None or not template.is_active:
            return None
        number = template.active_version_number
    else:
        if template is None:
            raise NotFoundError(f"No template exists for {document_type} at this facility.")
        number = version

    row = _version(template, number)
    content = TemplateContent.model_validate(row.content)
    return ResolvedTemplate(
        template_id=template.id,
        version_number=row.version_number,
        settings=RenderSettings(
            paper_size=row.paper_size,
            header_note=content.header_note,
            footer_text=content.footer_text,
            show_facility_contact=content.show_facility_contact,
            signature_labels=content.signature_labels,
            custom_width_mm=content.custom_width_mm,
            custom_height_mm=content.custom_height_mm,
        ),
    )
