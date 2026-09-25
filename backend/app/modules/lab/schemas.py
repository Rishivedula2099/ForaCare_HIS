import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

# P6-F01: fixed vocabularies for the Test/Parameter/ReferenceRange master
# screens. Kept as plain tuples (not a DB enum type), the same convention as
# `SERVICE_CATEGORIES`/`PAYMENT_MODES` in app/modules/billing/schemas.py.
SPECIMEN_TYPES = ("EDTA_BLOOD", "SERUM", "PLASMA", "URINE", "STOOL", "SWAB", "OTHER")
CONTAINER_TYPES = ("LAVENDER_TOP", "RED_TOP", "GRAY_TOP", "STERILE_CONTAINER", "OTHER")
REFERENCE_RANGE_GENDERS = ("ALL", "MALE", "FEMALE")


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
