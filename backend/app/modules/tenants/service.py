import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.modules.tenants.models import Tenant
from app.modules.tenants.schemas import TenantOut


async def list_tenants(db: AsyncSession) -> list[TenantOut]:
    result = await db.execute(select(Tenant).order_by(Tenant.name))
    return [TenantOut.model_validate(tenant) for tenant in result.scalars().all()]


async def get_tenant(db: AsyncSession, tenant_id: uuid.UUID) -> TenantOut:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise NotFoundError("Tenant not found.")
    return TenantOut.model_validate(tenant)
