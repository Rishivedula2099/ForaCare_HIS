import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ---------------------------------------------------------------------------
# P6-B01 / P6-F01: Lab Master (Test, Parameter, ReferenceRange)
# ---------------------------------------------------------------------------


class Test(Base):
    """The Lab Test Master (`MST-LAB-01`, P6-F01) - a billable, orderable
    test (`CBC`, `LIPID`, ...). `unit_price` mirrors `billing.Service.price`
    so a test can be priced/invoiced without a separate `billing_services`
    row; `tat_minutes` drives the turnaround-time expectation shown once
    accessioning/result-entry (P6-B02+) exists."""

    __tablename__ = "lab_tests"
    __table_args__ = (
        UniqueConstraint("facility_id", "test_code", name="uq_lab_tests_facility_id_test_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True
    )

    test_code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # EDTA_BLOOD | SERUM | PLASMA | URINE | STOOL | SWAB | OTHER
    specimen_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # LAVENDER_TOP | RED_TOP | GRAY_TOP | STERILE_CONTAINER | OTHER
    container_type: Mapped[str] = mapped_column(String(30), nullable=False)
    tat_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    department: Mapped["Department | None"] = relationship(lazy="selectin")  # noqa: F821
    parameters: Mapped[list["Parameter"]] = relationship(
        lazy="selectin", order_by="Parameter.sequence_order", cascade="all, delete-orphan"
    )


class Parameter(Base):
    """One reportable analyte of a `Test` (`MST-PAR-01`, P6-F01) - e.g. `HB`,
    `TLC`, `PLT` under `CBC`. Carries identity/display fields only; the
    normal/critical thresholds live on `ReferenceRange` because a single
    parameter can have several ranges (by gender/age band) - see
    `ReferenceRange` below."""

    __tablename__ = "lab_parameters"
    __table_args__ = (
        UniqueConstraint("test_id", "parameter_code", name="uq_lab_parameters_test_id_parameter_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_tests.id"), nullable=False
    )

    parameter_code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    reference_ranges: Mapped[list["ReferenceRange"]] = relationship(
        lazy="selectin", order_by="ReferenceRange.gender", cascade="all, delete-orphan"
    )


class ReferenceRange(Base):
    """A normal/critical band for a `Parameter`, scoped by `gender` and an
    age band in days (`age_min_days`/`age_max_days`, `None` upper bound
    meaning "no upper limit") so one parameter (e.g. Hemoglobin) can carry
    separate male/female ranges (`docs/masters.md` 3.3). Validated at the
    schema layer (`ReferenceRangeCreateRequest`/`...UpdateRequest`) against
    the masters.md rule `critical_low < normal_min < normal_max <
    critical_high`."""

    __tablename__ = "lab_reference_ranges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    parameter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_parameters.id"), nullable=False
    )

    # ALL | MALE | FEMALE
    gender: Mapped[str] = mapped_column(String(10), nullable=False, default="ALL")
    age_min_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    age_max_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    normal_min: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    normal_max: Mapped[float] = mapped_column(Numeric(12, 3), nullable=False)
    critical_low: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    critical_high: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# P6-B01: Lab workflow (Order -> Accession -> Sample -> Result -> Verification
# -> Approval). Schema/service/API for this half of P6-B01 lands in a later
# phase alongside accessioning/result-entry screens (P6-F02+); these tables
# exist now so the full lifecycle in `docs/requirements.md` SS4.5
# (`ORDER_PLACED -> BILLED -> ACCESSIONED -> SAMPLE_COLLECTED -> IN_TESTING ->
# RESULT_ENTERED -> VERIFIED_APPROVED -> REPORT_DISPATCHED`) has a home to
# migrate into incrementally.
# ---------------------------------------------------------------------------


class LabOrder(Base):
    """A single ordered test (P6-B01) - one row per (patient, test), the way
    `billing.InvoiceItem` is one row per billed line rather than one
    `Invoice` covering many tests. `accession_id` is set once the ordered
    test is folded into a specimen-tube accession event (see `Accession`);
    several `LabOrder`s sharing one blood draw share the same
    `accession_id`."""

    __tablename__ = "lab_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    test_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_tests.id"), nullable=False
    )
    encounter_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opd_encounters.id"), nullable=True
    )
    admission_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ipd_admissions.id"), nullable=True
    )
    ordered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=True
    )
    invoice_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("billing_invoice_items.id"), nullable=True
    )
    accession_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_accessions.id"), nullable=True
    )

    order_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    # ORDER_PLACED | BILLED | ACCESSIONED | SAMPLE_COLLECTED | IN_TESTING |
    # RESULT_ENTERED | VERIFIED_APPROVED | REPORT_DISPATCHED | CANCELLED
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ORDER_PLACED")
    # NORMAL | URGENT | STAT
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="NORMAL")
    clinical_notes: Mapped[str | None] = mapped_column(String(500), nullable=True)

    ordered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    test: Mapped["Test"] = relationship(lazy="selectin")


class Accession(Base):
    """The administrative event that receives one or more specimen tubes for
    a patient (`docs/requirements.md` SS4.5) - `accession_number` is the
    `LAB-YYMMDD-NNNN` barcode id printed on `TPL-LAB-BAR`. One `Accession`
    can cover several `LabOrder`s (drawn together) and several `Sample` tubes
    (different tubes for different tests drawn at the same visit)."""

    __tablename__ = "lab_accessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False
    )
    accessioned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    accession_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    # ACCESSIONED | SAMPLE_COLLECTED | IN_TESTING | COMPLETED | CANCELLED
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACCESSIONED")

    accessioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Sample(Base):
    """One physical specimen tube collected under an `Accession` - e.g. the
    single lavender-top EDTA tube used for a `CBC`, or a red-top serum tube
    shared by `LFT`+`LIPID`. `barcode_id` is what a Code 128/QR scan against
    the tube resolves to."""

    __tablename__ = "lab_samples"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    accession_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_accessions.id"), nullable=False
    )
    collected_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    barcode_id: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    specimen_type: Mapped[str] = mapped_column(String(30), nullable=False)
    container_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # PENDING_COLLECTION | COLLECTED | IN_TRANSIT | RECEIVED | REJECTED
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING_COLLECTION")
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    collected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class SampleStatus(Base):
    """Append-only status-transition log for a `Sample` (mirrors
    `ipd.BedTransfer`'s history-row pattern) - lets TAT (`Test.tat_minutes`)
    be measured against real collection/receipt timestamps instead of only
    the sample's current `status`."""

    __tablename__ = "lab_sample_status_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    sample_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_samples.id"), nullable=False
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    status: Mapped[str] = mapped_column(String(30), nullable=False)
    remarks: Mapped[str | None] = mapped_column(String(500), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class Result(Base):
    """The current entered value for one (`LabOrder`, `Parameter`) pair
    (P6-B01) - `flag` is auto-derived against the matching `ReferenceRange`
    at entry time (`docs/requirements.md` SS4.5: LOW/NORMAL/HIGH/CRITICAL).
    `current_version` mirrors the latest `ResultVersion` row so a report can
    render without a join; an amendment after approval bumps both."""

    __tablename__ = "lab_results"
    __table_args__ = (
        UniqueConstraint("lab_order_id", "parameter_id", name="uq_lab_results_order_id_parameter_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    lab_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_orders.id"), nullable=False
    )
    parameter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_parameters.id"), nullable=False
    )
    sample_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_samples.id"), nullable=True
    )
    entered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Stored as text (not Numeric) so a qualitative result (e.g. "Reactive",
    # "Nil") can share the same column as a numeric one.
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # LOW | NORMAL | HIGH | CRITICAL
    flag: Mapped[str] = mapped_column(String(20), nullable=False, default="NORMAL")
    # ENTERED | VERIFIED | APPROVED | AMENDED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ENTERED")
    current_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ResultVersion(Base):
    """Append-only history of every value a `Result` has ever held
    (`docs/requirements.md` SS4.5: "amendments post-approval require version
    increment (v1, v2) with logged audit justification"). `version_number 1`
    is written alongside the first `Result` insert; each amendment adds the
    next number rather than overwriting a prior row."""

    __tablename__ = "lab_result_versions"
    __table_args__ = (
        UniqueConstraint("result_id", "version_number", name="uq_lab_result_versions_result_id_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_results.id"), nullable=False
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[str] = mapped_column(String(100), nullable=False)
    flag: Mapped[str] = mapped_column(String(20), nullable=False)
    change_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class Verification(Base):
    """A technical verification pass over a `LabOrder`'s entered results
    (`lab.verify_results`) - the step between `RESULT_ENTERED` and the
    pathologist's `Approval`. Kept as its own append-only row (one order can
    be sent back and re-verified) rather than a single mutable flag on
    `LabOrder`."""

    __tablename__ = "lab_verifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    lab_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_orders.id"), nullable=False
    )
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # VERIFIED | REJECTED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="VERIFIED")
    remarks: Mapped[str | None] = mapped_column(String(500), nullable=True)

    verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class Approval(Base):
    """The pathologist's final sign-off on a `LabOrder`
    (`lab.approve_reports`, only `LAB_APPROVER` per `docs/requirements.md`
    SS4.5) - `report_checksum`/`report_qr_token` back the sealed PDF's public
    verification QR once the report-generation piece (P6-F0x) exists."""

    __tablename__ = "lab_approvals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    lab_order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lab_orders.id"), nullable=False
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # APPROVED | REJECTED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="APPROVED")
    remarks: Mapped[str | None] = mapped_column(String(500), nullable=True)
    report_checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    report_qr_token: Mapped[str | None] = mapped_column(String(128), nullable=True)

    approved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
