import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: uuid.UUID
    request_id: str | None
    tenant_id: uuid.UUID | None
    facility_id: uuid.UUID | None
    actor_user_id: uuid.UUID | None
    actor_username: str | None
    action: str
    resource_type: str
    resource_id: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}
