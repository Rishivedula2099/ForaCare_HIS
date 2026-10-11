import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DocumentTemplate(Base):
    """P7-B02: a facility's template for one document type.

    This row is only the mutable *pointer* (name, active flag, which version
    is live). The layout itself lives in immutable `DocumentTemplateVersion`
    rows, so changing a template never rewrites what an earlier version
    looked like.
    """

    __tablename__ = "document_templates"
    __table_args__ = (UniqueConstraint("facility_id", "document_type", name="uq_document_templates_facility_type"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    facility_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False)
    # Matches a `DocumentSpec.code` in documents/service.py (e.g. RECEIPT).
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Inactive -> the engine falls back to its built-in default layout.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # The version used when a caller doesn't ask for a specific one.
    active_version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    versions: Mapped[list["DocumentTemplateVersion"]] = relationship(
        back_populates="template", order_by="DocumentTemplateVersion.version_number", lazy="selectin"
    )


class DocumentTemplateVersion(Base):
    """An immutable snapshot of a template's layout (V1, V2, V3...).

    Never updated or deleted: a document generated under version N can be
    reproduced later by requesting version N, regardless of what newer
    versions say. "Editing" a template means inserting version N+1.
    """

    __tablename__ = "document_template_versions"
    __table_args__ = (UniqueConstraint("template_id", "version_number", name="uq_document_template_versions_number"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("document_templates.id"), nullable=False, index=True
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    # A4 | A5 | THERMAL_80
    paper_size: Mapped[str] = mapped_column(String(20), nullable=False)
    # Validated against `TemplateContent` in schemas.py.
    content: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    change_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    template: Mapped[DocumentTemplate] = relationship(back_populates="versions")
