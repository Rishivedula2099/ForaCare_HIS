"""P10-B02: staff management for a Hospital Admin, inside their own organisation."""
import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.core.permissions import require_permissions
from app.core.rate_limit import rate_limit
from app.core.responses import ApiResponse, success_response
from app.modules.auth.models import User
from app.modules.users import service
from app.modules.users.schemas import RoleRef, UserCreateRequest, UserUpdateRequest

router = APIRouter(prefix="/users", tags=["users"])
_limit = rate_limit("users-write", limit=get_settings().rate_limit_sensitive_per_minute * 3)


def _rid(request: Request):
    return getattr(request.state, "request_id", None)


@router.get("", response_model=ApiResponse, summary="List staff in your organisation")
async def list_users(
    request: Request,
    facility_id: uuid.UUID | None = Query(default=None, description="Only staff with access to this facility"),
    include_inactive: bool = Query(default=True),
    db: AsyncSession = Depends(get_db),
    caller: User = Depends(require_permissions("users.manage")),
):
    users = await service.list_users(db, caller, facility_id=facility_id, include_inactive=include_inactive)
    return success_response([u.model_dump(mode="json") for u in users], request_id=_rid(request))


@router.get("/assignable-roles", response_model=ApiResponse, summary="Roles you may give to staff")
async def assignable_roles(
    request: Request,
    db: AsyncSession = Depends(get_db),
    caller: User = Depends(require_permissions("users.manage")),
):
    roles = await service.assignable_roles(db)
    return success_response(
        [RoleRef(id=r.id, code=r.code, name=r.name).model_dump(mode="json") for r in roles], request_id=_rid(request)
    )


@router.get("/{user_id}", response_model=ApiResponse, summary="One staff member")
async def get_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    caller: User = Depends(require_permissions("users.manage")),
):
    return success_response((await service.get_user(db, user_id, caller)).model_dump(mode="json"), request_id=_rid(request))


@router.post(
    "", response_model=ApiResponse, status_code=201, summary="Invite a staff member", dependencies=[Depends(_limit)]
)
async def invite_user(
    payload: UserCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    caller: User = Depends(require_permissions("users.manage")),
):
    result = await service.invite_user(db, payload, caller)
    return success_response(result.model_dump(mode="json"), request_id=_rid(request))


@router.patch("/{user_id}", response_model=ApiResponse, summary="Change a staff member's details, role or facilities")
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    caller: User = Depends(require_permissions("users.manage")),
):
    result = await service.update_user(db, user_id, payload, caller)
    return success_response(result.model_dump(mode="json"), request_id=_rid(request))


@router.post("/{user_id}/deactivate", response_model=ApiResponse, summary="Deactivate a staff member and end their sessions")
async def deactivate_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    caller: User = Depends(require_permissions("users.manage")),
):
    result = await service.set_active(db, user_id, caller, active=False)
    return success_response(result.model_dump(mode="json"), request_id=_rid(request))


@router.post("/{user_id}/reactivate", response_model=ApiResponse, summary="Reactivate a staff member")
async def reactivate_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    caller: User = Depends(require_permissions("users.manage")),
):
    result = await service.set_active(db, user_id, caller, active=True)
    return success_response(result.model_dump(mode="json"), request_id=_rid(request))


@router.post(
    "/{user_id}/resend-activation",
    response_model=ApiResponse,
    summary="Issue a fresh activation link for someone who has never signed in",
    dependencies=[Depends(_limit)],
)
async def resend_activation(
    user_id: uuid.UUID,
    request: Request,
    send_email: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    caller: User = Depends(require_permissions("users.manage")),
):
    result = await service.resend_activation(db, user_id, caller, send_email=send_email)
    return success_response(result.model_dump(mode="json"), request_id=_rid(request))
