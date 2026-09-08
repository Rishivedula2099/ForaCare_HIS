import uuid

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permissions
from app.core.responses import ApiResponse, success_response
from app.modules.audit import service
from app.modules.auth.models import User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=ApiResponse, summary="List audit log entries for the current tenant")
async def list_audit_logs(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("audit.view_logs")),
    resource_type: str | None = Query(default=None),
    actor_user_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    logs = await service.list_audit_logs(
        db,
        tenant_id=current_user.tenant_id,
        resource_type=resource_type,
        actor_user_id=actor_user_id,
        limit=limit,
        offset=offset,
    )
    return success_response(
        [log.model_dump(mode="json") for log in logs],
        request_id=getattr(request.state, "request_id", None),
    )
