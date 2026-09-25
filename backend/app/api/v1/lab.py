import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permissions
from app.core.responses import ApiResponse, success_response
from app.modules.auth.models import User
from app.modules.lab import service
from app.modules.lab.schemas import (
    ParameterCreateRequest,
    ParameterUpdateRequest,
    ReferenceRangeCreateRequest,
    ReferenceRangeUpdateRequest,
    TestCreateRequest,
    TestUpdateRequest,
)

router = APIRouter(prefix="/lab", tags=["lab"])


def _ok(request: Request, data):
    return success_response(data, request_id=getattr(request.state, "request_id", None))


# ---------------------------------------------------------------------------
# Test master (P6-F01)
# ---------------------------------------------------------------------------


@router.get("/tests", response_model=ApiResponse, summary="List/search lab tests")
async def list_tests(
    request: Request,
    name: str | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    tests = await service.list_tests(db, current_user, name=name, is_active=is_active)
    return _ok(request, [item.model_dump(mode="json") for item in tests])


@router.get("/tests/{test_id}", response_model=ApiResponse, summary="Get a single lab test")
async def get_test(
    test_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    item = await service.get_test(db, test_id, current_user)
    return _ok(request, item.model_dump(mode="json"))


@router.post("/tests", response_model=ApiResponse, summary="Create a lab test")
async def create_test(
    payload: TestCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.manage_master")),
):
    item = await service.create_test(db, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))


@router.patch("/tests/{test_id}", response_model=ApiResponse, summary="Update a lab test")
async def update_test(
    test_id: uuid.UUID,
    payload: TestUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.manage_master")),
):
    item = await service.update_test(db, test_id, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Parameter master (nested under a Test)
# ---------------------------------------------------------------------------


@router.get(
    "/tests/{test_id}/parameters", response_model=ApiResponse, summary="List parameters for a lab test"
)
async def list_parameters(
    test_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    parameters = await service.list_parameters(db, test_id, current_user)
    return _ok(request, [item.model_dump(mode="json") for item in parameters])


@router.get("/parameters/{parameter_id}", response_model=ApiResponse, summary="Get a single lab parameter")
async def get_parameter(
    parameter_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    item = await service.get_parameter(db, parameter_id, current_user)
    return _ok(request, item.model_dump(mode="json"))


@router.post(
    "/tests/{test_id}/parameters", response_model=ApiResponse, summary="Add a parameter to a lab test"
)
async def create_parameter(
    test_id: uuid.UUID,
    payload: ParameterCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.manage_master")),
):
    item = await service.create_parameter(db, test_id, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))


@router.patch("/parameters/{parameter_id}", response_model=ApiResponse, summary="Update a lab parameter")
async def update_parameter(
    parameter_id: uuid.UUID,
    payload: ParameterUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.manage_master")),
):
    item = await service.update_parameter(db, parameter_id, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# ReferenceRange master (nested under a Parameter)
# ---------------------------------------------------------------------------


@router.get(
    "/parameters/{parameter_id}/reference-ranges",
    response_model=ApiResponse,
    summary="List reference ranges for a lab parameter",
)
async def list_reference_ranges(
    parameter_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    ranges = await service.list_reference_ranges(db, parameter_id, current_user)
    return _ok(request, [item.model_dump(mode="json") for item in ranges])


@router.post(
    "/parameters/{parameter_id}/reference-ranges",
    response_model=ApiResponse,
    summary="Add a reference range to a lab parameter",
)
async def create_reference_range(
    parameter_id: uuid.UUID,
    payload: ReferenceRangeCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.manage_master")),
):
    item = await service.create_reference_range(db, parameter_id, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))


@router.patch(
    "/reference-ranges/{reference_range_id}",
    response_model=ApiResponse,
    summary="Update a reference range",
)
async def update_reference_range(
    reference_range_id: uuid.UUID,
    payload: ReferenceRangeUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.manage_master")),
):
    item = await service.update_reference_range(db, reference_range_id, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))
