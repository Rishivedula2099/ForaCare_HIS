import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permissions
from app.core.responses import ApiResponse, success_response
from app.modules.tenants import service

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("", response_model=ApiResponse, summary="List all tenants")
async def list_tenants(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("tenants.manage")),
):
    tenants = await service.list_tenants(db)
    return success_response(
        [tenant.model_dump(mode="json") for tenant in tenants],
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/{tenant_id}", response_model=ApiResponse, summary="Get a single tenant")
async def get_tenant(
    tenant_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("tenants.manage")),
):
    tenant = await service.get_tenant(db, tenant_id)
    return success_response(
        tenant.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )
