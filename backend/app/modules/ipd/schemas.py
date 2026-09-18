import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

BedStatus = Literal["AVAILABLE", "RESERVED", "OCCUPIED", "CLEANING", "MAINTENANCE", "BLOCKED"]

# ---------------------------------------------------------------------------
# Ward
# ---------------------------------------------------------------------------


class WardOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    facility_id: uuid.UUID
    department_id: uuid.UUID | None = None
    name: str
    code: str
    ward_type: str
    floor: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WardCreateRequest(BaseModel):
    department_id: uuid.UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=20)
    ward_type: str = Field(default="GENERAL", max_length=20)
    floor: str | None = Field(default=None, max_length=20)


class WardUpdateRequest(BaseModel):
    department_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    ward_type: str | None = Field(default=None, max_length=20)
    floor: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# Room
# ---------------------------------------------------------------------------


class RoomOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    facility_id: uuid.UUID
    ward_id: uuid.UUID
    room_number: str
    room_type: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    ward: WardOut

    model_config = {"from_attributes": True}


class RoomCreateRequest(BaseModel):
    ward_id: uuid.UUID
    room_number: str = Field(min_length=1, max_length=20)
    room_type: str = Field(default="GENERAL", max_length=20)


class RoomUpdateRequest(BaseModel):
    room_number: str | None = Field(default=None, min_length=1, max_length=20)
    room_type: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# Bed
# ---------------------------------------------------------------------------


class PatientSummary(BaseModel):
    id: uuid.UUID
    uid: str
    mrn: str
    first_name: str
    middle_name: str | None = None
    last_name: str
    gender: str
    dob: str


class CurrentOccupant(BaseModel):
    admission_id: uuid.UUID
    admission_number: str
    admitted_at: datetime
    patient: PatientSummary


class BedOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    facility_id: uuid.UUID
    ward_id: uuid.UUID
    room_id: uuid.UUID
    bed_number: str
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    ward: WardOut
    room: RoomOut
    current_occupant: CurrentOccupant | None = None

    model_config = {"from_attributes": True}


class BedCreateRequest(BaseModel):
    ward_id: uuid.UUID
    room_id: uuid.UUID
    bed_number: str = Field(min_length=1, max_length=20)


class BedUpdateRequest(BaseModel):
    bed_number: str | None = Field(default=None, min_length=1, max_length=20)
    status: BedStatus | None = None
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# Admission / BedAssignment
# ---------------------------------------------------------------------------


class BedAssignmentOut(BaseModel):
    id: uuid.UUID
    admission_id: uuid.UUID
    bed_id: uuid.UUID
    status: str
    assigned_at: datetime
    released_at: datetime | None = None
    bed: BedOut

    model_config = {"from_attributes": True}


class AdmissionOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    facility_id: uuid.UUID
    patient_id: uuid.UUID
    admitting_doctor_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    admission_number: str
    admission_type: str
    status: str
    notes: str | None = None
    admitted_at: datetime
    created_at: datetime
    updated_at: datetime
    bed_assignments: list[BedAssignmentOut] = []

    model_config = {"from_attributes": True}


class AdmissionCreateRequest(BaseModel):
    patient_id: uuid.UUID
    bed_id: uuid.UUID
    admitting_doctor_id: uuid.UUID | None = None
    department_id: uuid.UUID | None = None
    admission_type: str = Field(default="ELECTIVE", max_length=20)
    notes: str | None = Field(default=None, max_length=1000)


# ---------------------------------------------------------------------------
# Transfer
# ---------------------------------------------------------------------------


class TransferOut(BaseModel):
    id: uuid.UUID
    admission_id: uuid.UUID
    from_bed_id: uuid.UUID | None = None
    to_bed_id: uuid.UUID
    reason: str | None = None
    transferred_at: datetime

    model_config = {"from_attributes": True}


class TransferCreateRequest(BaseModel):
    to_bed_id: uuid.UUID
    reason: str | None = Field(default=None, max_length=500)


# ---------------------------------------------------------------------------
# Discharge
# ---------------------------------------------------------------------------


class DischargeOut(BaseModel):
    id: uuid.UUID
    admission_id: uuid.UUID
    discharge_type: str
    discharge_condition: str | None = None
    discharge_summary: str | None = None
    follow_up_instructions: str | None = None
    discharged_at: datetime

    model_config = {"from_attributes": True}


class DischargeCreateRequest(BaseModel):
    discharge_type: str = Field(default="NORMAL", max_length=20)
    discharge_condition: str | None = Field(default=None, max_length=50)
    discharge_summary: str | None = Field(default=None, max_length=2000)
    follow_up_instructions: str | None = Field(default=None, max_length=1000)


# ---------------------------------------------------------------------------
# Consent
# ---------------------------------------------------------------------------


class ConsentOut(BaseModel):
    id: uuid.UUID
    admission_id: uuid.UUID
    consent_type: str
    consent_given: bool
    given_by_name: str
    relationship_to_patient: str | None = None
    notes: str | None = None
    recorded_at: datetime

    model_config = {"from_attributes": True}


class ConsentCreateRequest(BaseModel):
    consent_type: str = Field(min_length=1, max_length=30)
    consent_given: bool = True
    given_by_name: str = Field(min_length=1, max_length=255)
    relationship_to_patient: str | None = Field(default=None, max_length=50)
    notes: str | None = Field(default=None, max_length=1000)
