import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

AuthMethod = Literal["AADHAAR_OTP", "MOBILE_OTP"]
ConsentPurpose = Literal["CARE_MANAGEMENT", "HEALTH_RECORDS_SHARING", "RESEARCH"]


class OtpRequest(BaseModel):
    auth_method: AuthMethod
    identifier: str = Field(min_length=10, max_length=12, pattern=r"^\d+$")


class OtpChallengeOut(BaseModel):
    transaction_id: str
    message: str | None = None


class VerifyRequest(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=100)
    otp: str = Field(pattern=r"^\d{6}$")


class ConsentCreateRequest(BaseModel):
    purpose: ConsentPurpose


class ConsentOut(BaseModel):
    id: uuid.UUID
    purpose: str
    status: str
    granted_at: datetime
    revoked_at: datetime | None = None

    model_config = {"from_attributes": True}


class AbhaStatusOut(BaseModel):
    """A patient's ABHA state. `status` is UNVERIFIED -> VERIFIED -> LINKED."""

    patient_id: uuid.UUID
    status: str
    abha_number: str | None = None
    abha_address: str | None = None
    linked_at: datetime | None = None
    consents: list[ConsentOut] = Field(default_factory=list)
