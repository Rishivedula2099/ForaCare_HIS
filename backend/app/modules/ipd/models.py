import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# `Bed.status_code` (P4-B02) stores the bed's status as a small integer
# rather than its string label - every caller (app/modules/ipd/service.py)
# still reads/writes the string label via these maps; only the DB column and
# this raw attribute are numeric.
BED_STATUS_CODES: dict[str, int] = {
    "AVAILABLE": 1,
    "RESERVED": 2,
    "OCCUPIED": 3,
    "CLEANING": 4,
    "MAINTENANCE": 5,
    "BLOCKED": 6,
}
BED_STATUS_LABELS: dict[int, str] = {code: label for label, code in BED_STATUS_CODES.items()}


class Ward(Base):
    __tablename__ = "ipd_wards"

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

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    ward_type: Mapped[str] = mapped_column(String(20), nullable=False, default="GENERAL")
    floor: Mapped[str | None] = mapped_column(String(20), nullable=True)
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


class Room(Base):
    __tablename__ = "ipd_rooms"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    ward_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ipd_wards.id"), nullable=False
    )

    room_number: Mapped[str] = mapped_column(String(20), nullable=False)
    room_type: Mapped[str] = mapped_column(String(20), nullable=False, default="GENERAL")
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

    ward: Mapped["Ward"] = relationship(lazy="selectin")


class Bed(Base):
    __tablename__ = "ipd_beds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    ward_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ipd_wards.id"), nullable=False
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ipd_rooms.id"), nullable=False
    )

    bed_number: Mapped[str] = mapped_column(String(20), nullable=False)
    # See BED_STATUS_CODES/BED_STATUS_LABELS above.
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=BED_STATUS_CODES["AVAILABLE"])
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

    ward: Mapped["Ward"] = relationship(lazy="selectin")
    room: Mapped["Room"] = relationship(lazy="selectin")

    @property
    def status(self) -> str:
        return BED_STATUS_LABELS[self.status_code]

    @status.setter
    def status(self, value: str) -> None:
        self.status_code = BED_STATUS_CODES[value]


class Admission(Base):
    __tablename__ = "ipd_admissions"

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
    admitting_doctor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=True
    )
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True
    )
    admitted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    admission_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    # ELECTIVE | EMERGENCY | TRANSFER_IN
    admission_type: Mapped[str] = mapped_column(String(20), nullable=False, default="ELECTIVE")
    # ADMITTED | DISCHARGED | CANCELLED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ADMITTED")
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    admitted_at: Mapped[datetime] = mapped_column(
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

    # `selectin` avoids a lazy-load under the async engine (MissingGreenlet),
    # same rationale as `OPDEncounter.patient` etc in app/modules/opd/models.py.
    patient: Mapped["Patient"] = relationship(lazy="selectin")  # noqa: F821
    admitting_doctor: Mapped["Doctor | None"] = relationship(lazy="selectin")  # noqa: F821
    department: Mapped["Department | None"] = relationship(lazy="selectin")  # noqa: F821
    bed_assignments: Mapped[list["BedAssignment"]] = relationship(
        lazy="selectin", order_by="BedAssignment.assigned_at"
    )


class BedAssignment(Base):
    __tablename__ = "ipd_bed_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    admission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ipd_admissions.id"), nullable=False
    )
    bed_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ipd_beds.id"), nullable=False
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # ACTIVE | RELEASED. Exactly one ACTIVE row per admission at a time -
    # a service-layer invariant (see app/modules/ipd/service.py), not a DB
    # constraint, since "current" is temporal rather than a static shape.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    bed: Mapped["Bed"] = relationship(lazy="selectin")


class Transfer(Base):
    __tablename__ = "ipd_transfers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    admission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ipd_admissions.id"), nullable=False
    )
    from_bed_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ipd_beds.id"), nullable=True
    )
    to_bed_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ipd_beds.id"), nullable=False
    )
    transferred_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    transferred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    from_bed: Mapped["Bed | None"] = relationship(lazy="selectin", foreign_keys=[from_bed_id])
    to_bed: Mapped["Bed"] = relationship(lazy="selectin", foreign_keys=[to_bed_id])


class Consent(Base):
    __tablename__ = "ipd_consents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    admission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ipd_admissions.id"), nullable=False
    )
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # GENERAL_ADMISSION | SURGICAL | ANESTHESIA | HIGH_RISK | BLOOD_TRANSFUSION
    consent_type: Mapped[str] = mapped_column(String(30), nullable=False)
    consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    given_by_name: Mapped[str] = mapped_column(String(255), nullable=False)
    relationship_to_patient: Mapped[str | None] = mapped_column(String(50), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class Discharge(Base):
    __tablename__ = "ipd_discharges"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    admission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ipd_admissions.id"), nullable=False, unique=True
    )
    discharged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # NORMAL | DAMA | TRANSFER_OUT | DEATH
    discharge_type: Mapped[str] = mapped_column(String(20), nullable=False, default="NORMAL")
    discharge_condition: Mapped[str | None] = mapped_column(String(50), nullable=True)
    discharge_summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    follow_up_instructions: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    discharged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
