"""P10-B02: staff management inside one organisation (tenant)."""
import re
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

_USERNAME = re.compile(r"^[A-Za-z0-9._-]{3,100}$")
_PHONE = re.compile(r"^\+?[0-9][0-9 ()-]{6,19}$")


def _clean(value: str) -> str:
    return " ".join(value.split())


class RoleRef(BaseModel):
    id: uuid.UUID
    code: str
    name: str


class FacilityRef(BaseModel):
    id: uuid.UUID
    name: str
    facility_code: str
    is_active: bool
    is_default: bool


class UserAdminOut(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    phone: str | None
    full_name: str
    role: RoleRef
    is_active: bool
    facilities: list[FacilityRef]
    last_login_at: datetime | None
    # Invited but has never signed in (an activation link may still be outstanding).
    pending_activation: bool


class UserCreateRequest(BaseModel):
    username: str
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    role_id: uuid.UUID
    facility_ids: list[uuid.UUID] = Field(min_length=1, max_length=50)
    default_facility_id: uuid.UUID | None = None
    send_activation_email: bool = False

    @field_validator("username")
    @classmethod
    def _username(cls, v: str) -> str:
        v = v.strip()
        if not _USERNAME.match(v):
            raise ValueError("Use 3-100 letters, digits, '.', '_' or '-'.")
        return v

    @field_validator("full_name")
    @classmethod
    def _name(cls, v: str) -> str:
        return _clean(v)


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(default=None, max_length=20)
    role_id: uuid.UUID | None = None
    facility_ids: list[uuid.UUID] | None = Field(default=None, min_length=1, max_length=50)
    default_facility_id: uuid.UUID | None = None

    @field_validator("full_name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        return _clean(v) if v else v

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str | None) -> str | None:
        if v and not _PHONE.match(v.strip()):
            raise ValueError("Enter a valid phone number.")
        return v.strip() if v else v


class UserInvited(BaseModel):
    user: UserAdminOut
    # Shown once; only its hash is stored.
    activation_link: str
    activation_expires_hours: int
    activation_email_sent: bool
