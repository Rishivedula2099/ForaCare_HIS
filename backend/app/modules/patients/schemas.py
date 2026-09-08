import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class PatientAddressOut(BaseModel):
    address_type: str
    street: str
    city: str
    state: str
    pincode: str
    country: str

    model_config = {"from_attributes": True}


class PatientAddressIn(BaseModel):
    address_type: str = Field(default="PERMANENT", max_length=20)
    street: str = Field(min_length=1, max_length=500)
    city: str = Field(min_length=1, max_length=100)
    state: str = Field(min_length=1, max_length=100)
    pincode: str = Field(min_length=1, max_length=10)
    country: str = Field(default="India", max_length=100)


class PatientContactOut(BaseModel):
    contact_type: str
    value: str
    is_primary: bool

    model_config = {"from_attributes": True}


class PatientContactIn(BaseModel):
    contact_type: str = Field(max_length=20)
    value: str = Field(min_length=1, max_length=255)
    is_primary: bool = False


class PatientPhotoOut(BaseModel):
    id: uuid.UUID
    storage_path: str
    content_type: str | None = None
    is_primary: bool
    captured_at: datetime

    model_config = {"from_attributes": True}


class PatientIdentifierOut(BaseModel):
    identity_type: str
    id_number: str
    is_verified: bool
    verified_at: datetime | None = None

    model_config = {"from_attributes": True}


class PatientIdentifierIn(BaseModel):
    identity_type: str = Field(max_length=30)
    id_number: str = Field(min_length=1, max_length=100)


class PatientIdentityLinkOut(BaseModel):
    system: str
    external_id: str | None = None
    external_address: str | None = None
    status: str
    linked_at: datetime | None = None

    model_config = {"from_attributes": True}


class PatientListItem(BaseModel):
    id: uuid.UUID
    uid: str
    mrn: str
    first_name: str
    middle_name: str | None = None
    last_name: str
    gender: str
    dob: date
    status: str

    model_config = {"from_attributes": True}


class PatientOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    facility_id: uuid.UUID
    uid: str
    mrn: str
    title: str | None = None
    first_name: str
    middle_name: str | None = None
    last_name: str
    gender: str
    dob: date
    blood_group: str
    marital_status: str | None = None
    occupation: str | None = None
    preferred_language: str | None = None
    is_minor: bool
    guardian_name: str | None = None
    guardian_relationship: str | None = None
    guardian_phone: str | None = None
    guardian_address: str | None = None
    status: str
    registered_by: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime

    address: PatientAddressOut | None = None
    contacts: list[PatientContactOut] = Field(default_factory=list)
    photos: list[PatientPhotoOut] = Field(default_factory=list)
    identifiers: list[PatientIdentifierOut] = Field(default_factory=list)
    identity_links: list[PatientIdentityLinkOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PatientCreateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=20)
    first_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    gender: str = Field(max_length=20)
    dob: date
    blood_group: str = Field(default="UNKNOWN", max_length=20)
    marital_status: str | None = Field(default=None, max_length=20)
    occupation: str | None = Field(default=None, max_length=100)
    preferred_language: str | None = Field(default=None, max_length=50)

    guardian_name: str | None = Field(default=None, max_length=255)
    guardian_relationship: str | None = Field(default=None, max_length=30)
    guardian_phone: str | None = Field(default=None, max_length=20)
    guardian_address: str | None = Field(default=None, max_length=500)

    address: PatientAddressIn
    contacts: list[PatientContactIn] = Field(default_factory=list)
    identifiers: list[PatientIdentifierIn] = Field(default_factory=list)
