import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

# P6-F01: fixed vocabularies for the Test/Parameter/ReferenceRange master
# screens. Kept as plain tuples (not a DB enum type), the same convention as
# `SERVICE_CATEGORIES`/`PAYMENT_MODES` in app/modules/billing/schemas.py.
SPECIMEN_TYPES = ("EDTA_BLOOD", "SERUM", "PLASMA", "URINE", "STOOL", "SWAB", "OTHER")
CONTAINER_TYPES = ("LAVENDER_TOP", "RED_TOP", "GRAY_TOP", "STERILE_CONTAINER", "OTHER")
REFERENCE_RANGE_GENDERS = ("ALL", "MALE", "FEMALE")

# P6-B02: the LabOrder state machine's vocabulary - see
# app/modules/lab/service.py::LAB_ORDER_TRANSITIONS for the transition map.
LAB_ORDER_STATUSES = (
    "ORDERED",
    "BILLED",
    "ACCESSIONED",
    "COLLECTION_PENDING",
    "COLLECTED",
    "PROCESSING",
    "RESULT_ENTERED",
    "TECHNICALLY_VERIFIED",
    "PENDING_APPROVAL",
    "APPROVED",
    "FINALIZED",
    "CANCELLED",
)


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


class TestOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    facility_id: uuid.UUID
    department_id: uuid.UUID | None = None
    test_code: str
    name: str
    specimen_type: str
    container_type: str
    tat_minutes: int
    unit_price: float
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TestCreateRequest(BaseModel):
    test_code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=255)
    specimen_type: str
    container_type: str
    department_id: uuid.UUID | None = None
    tat_minutes: int = Field(default=60, gt=0)
    unit_price: float = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _validate_vocab(self) -> "TestCreateRequest":
        if self.specimen_type not in SPECIMEN_TYPES:
            raise ValueError(f"specimen_type must be one of {SPECIMEN_TYPES}")
        if self.container_type not in CONTAINER_TYPES:
            raise ValueError(f"container_type must be one of {CONTAINER_TYPES}")
        return self


class TestUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    specimen_type: str | None = None
    container_type: str | None = None
    department_id: uuid.UUID | None = None
    tat_minutes: int | None = Field(default=None, gt=0)
    unit_price: float | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @model_validator(mode="after")
    def _validate_vocab(self) -> "TestUpdateRequest":
        if self.specimen_type is not None and self.specimen_type not in SPECIMEN_TYPES:
            raise ValueError(f"specimen_type must be one of {SPECIMEN_TYPES}")
        if self.container_type is not None and self.container_type not in CONTAINER_TYPES:
            raise ValueError(f"container_type must be one of {CONTAINER_TYPES}")
        return self


# ---------------------------------------------------------------------------
# Parameter
# ---------------------------------------------------------------------------


class ParameterOut(BaseModel):
    id: uuid.UUID
    test_id: uuid.UUID
    parameter_code: str
    name: str
    unit: str | None = None
    sequence_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ParameterCreateRequest(BaseModel):
    parameter_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    unit: str | None = Field(default=None, max_length=50)
    sequence_order: int = Field(default=0, ge=0)


class ParameterUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    unit: str | None = Field(default=None, max_length=50)
    sequence_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# ReferenceRange
# ---------------------------------------------------------------------------


class ReferenceRangeOut(BaseModel):
    id: uuid.UUID
    parameter_id: uuid.UUID
    gender: str
    age_min_days: int
    age_max_days: int | None = None
    normal_min: float
    normal_max: float
    critical_low: float | None = None
    critical_high: float | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


def validate_reference_range_ordering(
    critical_low: float | None,
    normal_min: float,
    normal_max: float,
    critical_high: float | None,
) -> None:
    """`docs/masters.md` SS4: `critical_low < normal_min < normal_max <
    critical_high` - both critical bounds are optional (some parameters only
    define a normal band), so only the supplied ones are checked. Shared by
    the schema-level validators below and by
    `app/modules/lab/service.py::update_reference_range` (a partial PATCH
    only carries the fields that changed, so it re-validates against the
    row merged with those changes rather than the payload alone)."""
    if normal_min >= normal_max:
        raise ValueError("normal_min must be less than normal_max")
    if critical_low is not None and critical_low >= normal_min:
        raise ValueError("critical_low must be less than normal_min")
    if critical_high is not None and critical_high <= normal_max:
        raise ValueError("critical_high must be greater than normal_max")


class ReferenceRangeCreateRequest(BaseModel):
    gender: str = Field(default="ALL")
    age_min_days: int = Field(default=0, ge=0)
    age_max_days: int | None = Field(default=None, ge=0)
    normal_min: float
    normal_max: float
    critical_low: float | None = None
    critical_high: float | None = None

    @model_validator(mode="after")
    def _validate(self) -> "ReferenceRangeCreateRequest":
        if self.gender not in REFERENCE_RANGE_GENDERS:
            raise ValueError(f"gender must be one of {REFERENCE_RANGE_GENDERS}")
        if self.age_max_days is not None and self.age_max_days < self.age_min_days:
            raise ValueError("age_max_days must be greater than or equal to age_min_days")
        validate_reference_range_ordering(
            self.critical_low, self.normal_min, self.normal_max, self.critical_high
        )
        return self


class ReferenceRangeUpdateRequest(BaseModel):
    gender: str | None = None
    age_min_days: int | None = Field(default=None, ge=0)
    age_max_days: int | None = Field(default=None, ge=0)
    normal_min: float | None = None
    normal_max: float | None = None
    critical_low: float | None = None
    critical_high: float | None = None

    @model_validator(mode="after")
    def _validate(self) -> "ReferenceRangeUpdateRequest":
        if self.gender is not None and self.gender not in REFERENCE_RANGE_GENDERS:
            raise ValueError(f"gender must be one of {REFERENCE_RANGE_GENDERS}")
        if (
            self.age_min_days is not None
            and self.age_max_days is not None
            and self.age_max_days < self.age_min_days
        ):
            raise ValueError("age_max_days must be greater than or equal to age_min_days")
        return self


# ---------------------------------------------------------------------------
# LabOrder (P6-B02 state machine)
# ---------------------------------------------------------------------------


class LabOrderOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    facility_id: uuid.UUID
    patient_id: uuid.UUID
    test_id: uuid.UUID
    encounter_id: uuid.UUID | None = None
    admission_id: uuid.UUID | None = None
    ordered_by: uuid.UUID | None = None
    invoice_item_id: uuid.UUID | None = None
    accession_id: uuid.UUID | None = None
    order_number: str
    status: str
    priority: str
    clinical_notes: str | None = None
    ordered_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LabOrderStatusUpdateRequest(BaseModel):
    status: str
    remarks: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate(self) -> "LabOrderStatusUpdateRequest":
        if self.status not in LAB_ORDER_STATUSES:
            raise ValueError(f"status must be one of {LAB_ORDER_STATUSES}")
        return self


class LabOrderStatusHistoryOut(BaseModel):
    id: uuid.UUID
    lab_order_id: uuid.UUID
    status: str
    remarks: str | None = None
    changed_by: uuid.UUID | None = None
    changed_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Accession / Sample (P6-B03 barcode generation, validation, resolution)
# ---------------------------------------------------------------------------


class AccessionOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    facility_id: uuid.UUID
    patient_id: uuid.UUID
    accessioned_by: uuid.UUID | None = None
    accession_number: str
    status: str
    accessioned_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AccessionCreateRequest(BaseModel):
    patient_id: uuid.UUID
    lab_order_ids: list[uuid.UUID] = Field(min_length=1)


class SampleOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    facility_id: uuid.UUID
    accession_id: uuid.UUID
    collected_by: uuid.UUID | None = None
    barcode_id: str
    specimen_type: str
    container_type: str
    status: str
    rejection_reason: str | None = None
    collected_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SampleCollectRequest(BaseModel):
    specimen_type: str
    container_type: str
    lab_order_ids: list[uuid.UUID] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_vocab(self) -> "SampleCollectRequest":
        if self.specimen_type not in SPECIMEN_TYPES:
            raise ValueError(f"specimen_type must be one of {SPECIMEN_TYPES}")
        if self.container_type not in CONTAINER_TYPES:
            raise ValueError(f"container_type must be one of {CONTAINER_TYPES}")
        return self


class SampleMarkCollectedRequest(BaseModel):
    remarks: str | None = Field(default=None, max_length=500)


class SampleRejectRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class SampleStatusHistoryOut(BaseModel):
    id: uuid.UUID
    sample_id: uuid.UUID
    status: str
    remarks: str | None = None
    changed_by: uuid.UUID | None = None
    changed_at: datetime

    model_config = {"from_attributes": True}


class BarcodeResolveResponse(BaseModel):
    """What a scan-workflow lookup of a tube/accession label resolves to
    (`service.resolve_barcode`) - exactly one of `accession`/`sample` is set,
    matching whichever table the scanned code matched."""

    code_type: str  # "ACCESSION" | "SAMPLE"
    accession: AccessionOut
    sample: SampleOut | None = None
    lab_orders: list[LabOrderOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Result (P6-B05 result engine / P6-F05 result entry)
# ---------------------------------------------------------------------------

# LOW | NORMAL | HIGH | CRITICAL - server-computed only (service._calculate_flag),
# never accepted as client input.
RESULT_FLAGS = ("LOW", "NORMAL", "HIGH", "CRITICAL")


class ResultOut(BaseModel):
    id: uuid.UUID
    lab_order_id: uuid.UUID
    parameter_id: uuid.UUID
    sample_id: uuid.UUID | None = None
    entered_by: uuid.UUID | None = None
    value: str
    unit: str | None = None
    flag: str
    status: str
    current_version: int
    entered_at: datetime

    model_config = {"from_attributes": True}


class ResultEntryItem(BaseModel):
    parameter_id: uuid.UUID
    value: str = Field(min_length=1, max_length=100)
    unit: str | None = Field(default=None, max_length=50)


class ResultEntryRequest(BaseModel):
    items: list[ResultEntryItem] = Field(min_length=1)


class ResultEntryFieldOut(BaseModel):
    """One dynamic field in the P6-F05 entry form - the parameter's identity,
    the reference range resolved for this patient (gender/age banded, `None`
    if no band matches), and the currently-saved value/flag if a `Result`
    already exists for this (order, parameter)."""

    parameter_id: uuid.UUID
    parameter_code: str
    name: str
    unit: str | None = None
    normal_min: float | None = None
    normal_max: float | None = None
    critical_low: float | None = None
    critical_high: float | None = None
    value: str | None = None
    flag: str | None = None


class ResultEntryFormOut(BaseModel):
    lab_order_id: uuid.UUID
    order_number: str
    order_status: str
    test_name: str
    fields: list[ResultEntryFieldOut]


class ResultVersionOut(BaseModel):
    id: uuid.UUID
    result_id: uuid.UUID
    changed_by: uuid.UUID | None = None
    version_number: int
    value: str
    flag: str
    change_reason: str | None = None
    recorded_at: datetime

    model_config = {"from_attributes": True}


class ResultAmendRequest(BaseModel):
    """P6-B06: the only way to change a `Result` once its `LabOrder` has
    been `APPROVED`/`FINALIZED` - a mandatory `reason` is what keeps this
    from being a silent overwrite of an approved result."""

    value: str = Field(min_length=1, max_length=100)
    unit: str | None = Field(default=None, max_length=50)
    reason: str = Field(min_length=1, max_length=500)


# ---------------------------------------------------------------------------
# Verification / Approval (P6-F06 technical verification & authorized
# approval workflow)
# ---------------------------------------------------------------------------


class VerificationOut(BaseModel):
    id: uuid.UUID
    lab_order_id: uuid.UUID
    verified_by: uuid.UUID | None = None
    status: str
    remarks: str | None = None
    verified_at: datetime

    model_config = {"from_attributes": True}


class VerifyResultsRequest(BaseModel):
    remarks: str | None = Field(default=None, max_length=500)


class RejectVerificationRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class ApprovalOut(BaseModel):
    id: uuid.UUID
    lab_order_id: uuid.UUID
    approved_by: uuid.UUID | None = None
    status: str
    remarks: str | None = None
    report_checksum: str | None = None
    report_qr_token: str | None = None
    approved_at: datetime

    model_config = {"from_attributes": True}


class ApproveResultsRequest(BaseModel):
    remarks: str | None = Field(default=None, max_length=500)


class RejectApprovalRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


# ---------------------------------------------------------------------------
# Report (P6-F07 lab report UI) - built only once an order is APPROVED/
# FINALIZED; the verification QR encodes `/verify/doc?t=LAB_REPORT&id=
# <lab_order_id>&sig=<report_qr_token>` (`docs/document-templates.md` SS3.1).
# ---------------------------------------------------------------------------


class ReportResultRow(BaseModel):
    parameter_id: uuid.UUID
    parameter_code: str
    parameter_name: str
    value: str
    unit: str | None = None
    normal_min: float | None = None
    normal_max: float | None = None
    critical_low: float | None = None
    critical_high: float | None = None
    flag: str
    # P6-B08 "apply correct version": always the row's *current*
    # `Result.current_version` - a report regenerated after `amend_result`
    # reflects the amendment immediately, and `is_amended` flags that for
    # display so a reader knows this supersedes an earlier printed copy.
    version: int
    is_amended: bool


class LabReportOut(BaseModel):
    lab_order_id: uuid.UUID
    order_number: str
    accession_number: str | None = None
    status: str
    test_name: str
    priority: str
    ordered_at: datetime
    collected_at: datetime | None = None

    facility_name: str
    facility_code: str

    patient_name: str
    patient_uid: str
    patient_mrn: str
    patient_gender: str
    patient_age_years: int

    referring_doctor_name: str | None = None

    rows: list[ReportResultRow]

    verified_by_name: str | None = None
    verified_at: datetime | None = None
    approved_by_name: str | None = None
    approved_at: datetime | None = None

    report_checksum: str | None = None
    report_qr_token: str | None = None
    generated_at: datetime


class LabReportVerifyOut(BaseModel):
    valid: bool
    document_type: str = "LAB_REPORT"
    order_number: str | None = None
    status: str | None = None
    facility_name: str | None = None
    approved_at: datetime | None = None
