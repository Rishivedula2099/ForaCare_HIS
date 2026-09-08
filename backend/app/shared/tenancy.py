import uuid

from sqlalchemy import ForeignKey, Select
from sqlalchemy.orm import Mapped, mapped_column, declared_attr
from sqlalchemy.dialects.postgresql import UUID

from app.core.context import get_current_facility_id, get_current_tenant_id
from app.core.exceptions import AppError


class TenantContextMissingError(AppError):
    """Raised when a tenant-scoped query runs with no authenticated request context."""

    code = "TENANT_CONTEXT_MISSING"
    status_code = 500


class TenantScopedMixin:
    """Adds tenant/facility columns to a domain model.

    Every table that stores hospital data (patients, encounters, invoices,
    etc.) should mix this in so it can be filtered with `scope_to_tenant`
    below and carries the FKs needed for cross-tenant protection checks.
    """

    @declared_attr
    def tenant_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True)

    @declared_attr
    def facility_id(cls) -> Mapped[uuid.UUID]:
        return mapped_column(UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False, index=True)


def scope_to_tenant(stmt: Select, model: type, *, facility_scoped: bool = True) -> Select:
    """Filters a SELECT to the current request's tenant (and facility).

    Reads tenant/facility from the request-scoped context set by
    `get_current_user`, so callers never need to pass the current user
    through service functions just to enforce isolation. Raises if called
    outside an authenticated request context, since an unscoped query would
    otherwise silently return every tenant's rows.
    """
    tenant_id = get_current_tenant_id()
    if tenant_id is None:
        raise TenantContextMissingError("No tenant context is set for this request.")
    stmt = stmt.where(model.tenant_id == tenant_id)

    if facility_scoped:
        facility_id = get_current_facility_id()
        if facility_id is None:
            raise TenantContextMissingError("No facility context is set for this request.")
        stmt = stmt.where(model.facility_id == facility_id)

    return stmt
