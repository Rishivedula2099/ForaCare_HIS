import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DoctorDepartmentOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str

    model_config = {"from_attributes": True}


class DoctorOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    facility_id: uuid.UUID
    department_id: uuid.UUID
    doctor_code: str
    full_name: str
    specialization: str
    qualification: str | None = None
    phone: str | None = None
    email: str | None = None
    consultation_fee: float | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    department: DoctorDepartmentOut

    model_config = {"from_attributes": True}


class DoctorCreateRequest(BaseModel):
    department_id: uuid.UUID
    full_name: str = Field(min_length=1, max_length=255)
    specialization: str = Field(min_length=1, max_length=255)
    qualification: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    consultation_fee: float | None = Field(default=None, ge=0)


class DoctorUpdateRequest(BaseModel):
    department_id: uuid.UUID | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    specialization: str | None = Field(default=None, min_length=1, max_length=255)
    qualification: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    email: str | None = Field(default=None, max_length=255)
    consultation_fee: float | None = Field(default=None, ge=0)
    is_active: bool | None = None
