import uuid
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class PatientSummaryOut(BaseModel):
    id: uuid.UUID
    uid: str
    mrn: str
    first_name: str
    middle_name: str | None = None
    last_name: str
    gender: str
    dob: date

    model_config = {"from_attributes": True}


class DepartmentSummaryOut(BaseModel):
    id: uuid.UUID
    name: str
    code: str

    model_config = {"from_attributes": True}


class DoctorSummaryOut(BaseModel):
    id: uuid.UUID
    doctor_code: str
    full_name: str
    specialization: str

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    id: uuid.UUID
    token_number: int
    token_date: date
    status: str
    priority: str
    called_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class TokenStatusUpdateRequest(BaseModel):
    status: str = Field(min_length=1, max_length=20)


class EncounterOut(BaseModel):
    id: uuid.UUID
    encounter_number: str
    visit_type: str
    status: str
    notes: str | None = None
    scheduled_at: datetime | None = None
    created_at: datetime
    patient: PatientSummaryOut
    department: DepartmentSummaryOut
    doctor: DoctorSummaryOut
    token: TokenOut | None = None
    qr_code: str
    qr_status: str
    qr_expires_at: datetime

    model_config = {"from_attributes": True}


class EncounterCreateRequest(BaseModel):
    patient_id: uuid.UUID
    department_id: uuid.UUID
    doctor_id: uuid.UUID
    visit_type: str = Field(default="WALK_IN", max_length=20)
    priority: str = Field(default="NORMAL", max_length=20)
    scheduled_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=1000)


class QRVerifyRequest(BaseModel):
    qr_code: str = Field(min_length=1, max_length=64)


class QRVerifyResult(BaseModel):
    valid: bool
    reason: str
    encounter: EncounterOut | None = None


# ---------------------------------------------------------------------------
# Consultation (P3-F05/P3-B04)
# ---------------------------------------------------------------------------


class VitalsIn(BaseModel):
    temperature_celsius: float | None = Field(default=None, ge=25, le=45)
    pulse_bpm: int | None = Field(default=None, ge=20, le=250)
    bp_systolic: int | None = Field(default=None, ge=50, le=260)
    bp_diastolic: int | None = Field(default=None, ge=30, le=180)
    spo2_percent: int | None = Field(default=None, ge=0, le=100)
    respiratory_rate: int | None = Field(default=None, ge=5, le=80)
    weight_kg: float | None = Field(default=None, ge=0, le=500)
    height_cm: float | None = Field(default=None, ge=0, le=300)


class ConsultationCreateRequest(BaseModel):
    chief_complaint: str | None = Field(default=None, max_length=1000)
    history: str | None = Field(default=None, max_length=2000)
    examination: str | None = Field(default=None, max_length=2000)
    diagnosis: str | None = Field(default=None, max_length=1000)
    allergies: str | None = Field(default=None, max_length=1000)
    investigation: str | None = Field(default=None, max_length=1000)
    treatment: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)
    vitals: VitalsIn = Field(default_factory=VitalsIn)


class ConsultationUpdateRequest(BaseModel):
    chief_complaint: str | None = Field(default=None, max_length=1000)
    history: str | None = Field(default=None, max_length=2000)
    examination: str | None = Field(default=None, max_length=2000)
    diagnosis: str | None = Field(default=None, max_length=1000)
    allergies: str | None = Field(default=None, max_length=1000)
    investigation: str | None = Field(default=None, max_length=1000)
    treatment: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)
    vitals: VitalsIn | None = None
    status: str | None = Field(default=None, max_length=20)


class ConsultationOut(BaseModel):
    id: uuid.UUID
    encounter_id: uuid.UUID
    doctor_id: uuid.UUID
    status: str
    chief_complaint: str | None = None
    history: str | None = None
    examination: str | None = None
    diagnosis: str | None = None
    allergies: str | None = None
    investigation: str | None = None
    treatment: str | None = None
    notes: str | None = None
    temperature_celsius: float | None = None
    pulse_bpm: int | None = None
    bp_systolic: int | None = None
    bp_diastolic: int | None = None
    spo2_percent: int | None = None
    respiratory_rate: int | None = None
    weight_kg: float | None = None
    height_cm: float | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    encounter: EncounterOut
    doctor: DoctorSummaryOut

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Prescription (P3-F06/P3-B05)
# ---------------------------------------------------------------------------

class DrugRoute(str, Enum):
    ORAL = "ORAL"
    IV = "IV"
    IM = "IM"
    SC = "SC"
    TOPICAL = "TOPICAL"
    INHALATION = "INHALATION"
    SUBLINGUAL = "SUBLINGUAL"
    RECTAL = "RECTAL"
    OTHER = "OTHER"


class PrescriptionItemIn(BaseModel):
    drug_name: str = Field(min_length=1, max_length=255)
    dosage: str = Field(min_length=1, max_length=100)
    route: DrugRoute
    frequency: str = Field(min_length=1, max_length=100)
    duration: str = Field(min_length=1, max_length=100)
    instructions: str | None = Field(default=None, max_length=500)

    @field_validator("drug_name", "dosage", "frequency", "duration")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("This field cannot be blank.")
        return stripped

    @field_validator("dosage")
    @classmethod
    def _dosage_has_quantity(cls, value: str) -> str:
        """A dosage without any digit ("some", "as needed") is almost
        always a data-entry mistake, not a real prescription line - catch
        it here rather than letting it silently reach the pharmacy/patient."""
        if not any(char.isdigit() for char in value):
            raise ValueError("Dosage must include a quantity (e.g. '500mg', '2 tablets').")
        return value


class PrescriptionItemOut(BaseModel):
    id: uuid.UUID
    drug_name: str
    dosage: str
    route: str
    frequency: str
    duration: str
    instructions: str | None = None

    model_config = {"from_attributes": True}


class PrescriptionCreateRequest(BaseModel):
    items: list[PrescriptionItemIn] = Field(min_length=1, max_length=30)


class PrescriptionUpdateRequest(BaseModel):
    items: list[PrescriptionItemIn] = Field(min_length=1, max_length=30)


class PrescriptionOut(BaseModel):
    id: uuid.UUID
    consultation_id: uuid.UUID
    doctor_id: uuid.UUID
    items: list[PrescriptionItemOut]
    created_at: datetime
    updated_at: datetime
    doctor: DoctorSummaryOut

    model_config = {"from_attributes": True}
