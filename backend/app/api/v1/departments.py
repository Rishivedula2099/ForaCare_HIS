import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permissions
from app.core.responses import ApiResponse, success_response
from app.modules.auth.models import User
from app.modules.departments import service
from app.modules.departments.schemas import DepartmentCreateRequest, DepartmentUpdateRequest

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=ApiResponse, summary="List/search departments in the current facility")
async def list_departments(
    request: Request,
    name: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("departments.view")),
):
    departments = await service.list_departments(db, current_user, name=name)
    return success_response(
        [department.model_dump(mode="json") for department in departments],
        request_id=getattr(request.state, "request_id", None),
    )


@router.get("/{department_id}", response_model=ApiResponse, summary="Get a single department")
async def get_department(
    department_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("departments.view")),
):
    department = await service.get_department(db, department_id, current_user)
    return success_response(
        department.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("", response_model=ApiResponse, summary="Create a department in the current facility")
async def create_department(
    payload: DepartmentCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("departments.manage")),
):
    department = await service.create_department(db, payload, current_user)
    return success_response(
        department.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )


@router.patch("/{department_id}", response_model=ApiResponse, summary="Update a department")
async def update_department(
    department_id: uuid.UUID,
    payload: DepartmentUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("departments.manage")),
):
    department = await service.update_department(db, department_id, payload, current_user)
    return success_response(
        department.model_dump(mode="json"),
        request_id=getattr(request.state, "request_id", None),
    )
