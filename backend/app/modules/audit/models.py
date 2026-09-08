import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    """An immutable record of a single auditable event.

    Rows are append-only: nothing in this codebase should ever update or
    delete an AuditLog after insert. `actor_username` is denormalized
    (copied at write time rather than joined from `users`) so the trail
    still reads correctly after a user is renamed or removed.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_tenant_created_at", "tenant_id", "created_at"),
        Index("ix_audit_logs_resource", "resource_type", "resource_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True
    )
    facility_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=True
    )

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    actor_username: Mapped[str | None] = mapped_column(String(100), nullable=True)

    action: Mapped[str] = mapped_column(String(150), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    before: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    after: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
