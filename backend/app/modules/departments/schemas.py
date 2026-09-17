import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DepartmentOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    facility_id: uuid.UUID
    name: str
    code: str
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DepartmentCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=20)
    description: str | None = Field(default=None, max_length=500)


class DepartmentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None
