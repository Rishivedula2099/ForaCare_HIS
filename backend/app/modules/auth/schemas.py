import uuid

from pydantic import BaseModel, EmailStr, Field

from app.modules.auth.models import User


class LoginRequest(BaseModel):
    username: str
    password: str
    facility_id: uuid.UUID | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TenantOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    code: str
    is_active: bool

    model_config = {"from_attributes": True}


class FacilityOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    facility_code: str
    address: str | None = None
    phone: str | None = None
    timezone: str
    currency: str
    is_active: bool

    model_config = {"from_attributes": True}


class RoleOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr
    full_name: str
    role: RoleOut
    permissions: list[str]
    tenant_id: uuid.UUID
    facility_id: uuid.UUID
    is_active: bool

    model_config = {"from_attributes": True}

    @classmethod
    def from_user(cls, user: User) -> "UserOut":
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=RoleOut.model_validate(user.role),
            permissions=sorted({permission.code for permission in user.role.permissions}),
            tenant_id=user.tenant_id,
            facility_id=user.facility_id,
            is_active=user.is_active,
        )


class LoginResponse(BaseModel):
    user: UserOut
    tenant: TenantOut
    facility: FacilityOut
    tokens: TokenResponse


class MeResponse(BaseModel):
    user: UserOut
    tenant: TenantOut
    facility: FacilityOut
