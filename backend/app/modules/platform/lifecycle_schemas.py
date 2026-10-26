"""P10-B02: request/response shapes for organisation (tenant) lifecycle."""
import uuid

from pydantic import BaseModel, Field, field_validator

from app.modules.platform.schemas import AdministratorInput, FacilityInput, _clean


class TenantUpdateRequest(BaseModel):
    """Organisations are renamed, never re-coded: the code is baked into identifiers."""

    name: str = Field(min_length=2, max_length=255)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return _clean(v)


class AssignAdministratorRequest(BaseModel):
    facility_id: uuid.UUID
    administrator: AdministratorInput
    send_activation_email: bool = False


class FacilityCreateInTenantRequest(BaseModel):
    facility: FacilityInput


class TenantSummary(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    is_active: bool
    status_reason: str | None
    facility_count: int
    active_facility_count: int
    user_count: int


class AdministratorSummary(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    full_name: str
    is_active: bool
    pending_activation: bool


class TenantDetail(TenantSummary):
    facilities: list[dict]
    administrators: list[AdministratorSummary]


class AdministratorAssigned(BaseModel):
    administrator_id: uuid.UUID
    administrator_username: str
    administrator_email: str
    facility_id: uuid.UUID
    # Shown once; only its hash is stored.
    activation_link: str
    activation_expires_hours: int
    activation_email_sent: bool
