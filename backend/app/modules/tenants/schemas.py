import uuid

from pydantic import BaseModel


class TenantOut(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    code: str
    is_active: bool

    model_config = {"from_attributes": True}
