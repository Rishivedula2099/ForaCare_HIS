import uuid

from pydantic import BaseModel, Field


class FacilityOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    facility_code: str
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    timezone: str
    currency: str
    is_active: bool

    model_config = {"from_attributes": True}


class FacilityCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    facility_code: str = Field(min_length=1, max_length=50)
    address: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    timezone: str = Field(default="Asia/Kolkata", max_length=50)
    currency: str = Field(default="INR", max_length=10)


class FacilityUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    timezone: str | None = Field(default=None, max_length=50)
    currency: str | None = Field(default=None, max_length=10)
    is_active: bool | None = None
