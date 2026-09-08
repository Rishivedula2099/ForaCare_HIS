import uuid

from pydantic import BaseModel


class PermissionOut(BaseModel):
    id: uuid.UUID
    code: str
    module: str
    description: str

    model_config = {"from_attributes": True}


class RoleSummaryOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None = None
    is_system: bool
    permission_count: int

    model_config = {"from_attributes": True}


class RoleDetailOut(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    description: str | None = None
    is_system: bool
    permissions: list[PermissionOut]

    model_config = {"from_attributes": True}


class UpdateRolePermissionsRequest(BaseModel):
    permission_ids: list[uuid.UUID]
