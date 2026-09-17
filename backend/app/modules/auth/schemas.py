import uuid

from pydantic import BaseModel, EmailStr, Field

from app.modules.auth.models import User
from app.modules.facilities.schemas import FacilityOut
from app.modules.tenants.schemas import TenantOut


class LoginRequest(BaseModel):
    username: str
    password: str
    facility_id: uuid.UUID | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class SessionMeta(BaseModel):
    """Non-secret session metadata returned alongside cookie-based tokens.

    The actual access/refresh JWTs never appear in a response body - they
    are set as HttpOnly cookies by the endpoint handler.
    """

    token_type: str = "bearer"
    expires_in: int


class RoleOut(BaseModel):
    id: uuid.UUID
    numeric_code: int
    code: str
    name: str

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr
    phone: str | None
    full_name: str
    role: RoleOut
    permissions: list[str]
    tenant_id: uuid.UUID
    facility_id: uuid.UUID
    is_active: bool
    email_verified: bool
    phone_verified: bool
    # P3-F07: the `doctors` row this login is clinically tied to, if any
    # (via `Doctor.user_id`). Lets the frontend proactively tell "you are
    # not the assigned doctor for this encounter" apart from "you lack the
    # RBAC permission entirely", instead of only finding out from a 403
    # after attempting to save - see `_ensure_is_assigned_doctor` in
    # app/modules/opd/service.py, which this field mirrors client-side.
    doctor_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_user(cls, user: User, *, doctor_id: uuid.UUID | None = None) -> "UserOut":
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            phone=user.phone,
            full_name=user.full_name,
            role=RoleOut.model_validate(user.role),
            permissions=sorted({permission.code for permission in user.role.permissions}),
            tenant_id=user.tenant_id,
            facility_id=user.facility_id,
            is_active=user.is_active,
            email_verified=user.email_verified_at is not None,
            phone_verified=user.phone_verified_at is not None,
            doctor_id=doctor_id,
        )


class LoginResponse(BaseModel):
    user: UserOut
    tenant: TenantOut
    facility: FacilityOut
    session: SessionMeta


class MeResponse(BaseModel):
    user: UserOut
    tenant: TenantOut
    facility: FacilityOut


class RequestEmailChangeRequest(BaseModel):
    new_email: EmailStr


class VerifyEmailChangeRequest(BaseModel):
    new_email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class RequestPhoneChangeRequest(BaseModel):
    new_phone: str = Field(min_length=7, max_length=20)


class VerifyPhoneChangeRequest(BaseModel):
    new_phone: str = Field(min_length=7, max_length=20)
    code: str = Field(min_length=6, max_length=6)


class OtpRequestedResponse(BaseModel):
    requested: bool = True
    expires_in_minutes: int
    # Only populated in local/dev environments so the flow is testable
    # without a real email/SMS provider wired up. Never populated otherwise.
    debug_code: str | None = None
