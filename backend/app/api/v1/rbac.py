import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permissions
from app.core.responses import ApiResponse, success_response
from app.modules.rbac import service
from app.modules.rbac.schemas import UpdateRolePermissionsRequest

router = APIRouter(prefix="/rbac", tags=["rbac"])


@router.get("/roles", response_model=ApiResponse, summary="List all roles")
async def list_roles(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("roles.view")),
):
    roles = await service.list_roles(db)
    return success_response(
        [role.model_dump(mode="json") for role in roles],
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/roles/{role_id}", response_model=ApiResponse, summary="Get a role and its permissions")
async def get_role(
    role_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("roles.view")),
):
    role = await service.get_role(db, role_id)
    return success_response(
        role.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/permissions", response_model=ApiResponse, summary="List all permissions")
async def list_permissions(
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("roles.view")),
):
    permissions = await service.list_permissions(db)
    return success_response(
        [permission.model_dump(mode="json") for permission in permissions],
        request_id=getattr(request.state, "request_id", None),
    )


@router.patch(
    "/roles/{role_id}/permissions",
    response_model=ApiResponse,
    summary="Replace a role's permission assignments",
)
async def update_role_permissions(
    role_id: uuid.UUID,
    payload: UpdateRolePermissionsRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permissions("roles.manage")),
):
    role = await service.set_role_permissions(db, role_id, payload.permission_ids)
    return success_response(
        role.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )
