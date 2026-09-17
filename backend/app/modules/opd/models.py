import uuid
from datetime import date as date_, datetime, time, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class OPDEncounter(Base):
    """A single OPD visit (walk-in or appointment) - the record created by
    Registration (P3-F02). Everything downstream (Token, Consultation,
    Prescription) hangs off this."""

    __tablename__ = "opd_encounters"

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
    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id"), nullable=False
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False
    )
    registered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    encounter_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    visit_type: Mapped[str] = mapped_column(String(20), nullable=False, default="WALK_IN")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="REGISTERED")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # P3-F04 QR check-in: an opaque, unguessable code (not the encounter id
    # itself, so a QR can't be forged just by knowing/enumerating ids).
    # "Expired" is derived (end of the day it was registered) rather than
    # stored; "revoked" is explicit staff action or set automatically when
    # the visit is cancelled - see app/modules/opd/service.py.
    qr_code: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    qr_status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    qr_revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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
    # same rationale as `Patient.address` etc in app/modules/patients/models.py.
    patient: Mapped["Patient"] = relationship(lazy="selectin")  # noqa: F821
    department: Mapped["Department"] = relationship(lazy="selectin")  # noqa: F821
    doctor: Mapped["Doctor"] = relationship(lazy="selectin")  # noqa: F821
    token: Mapped["Token | None"] = relationship(lazy="selectin", uselist=False)

    @property
    def qr_expires_at(self) -> datetime:
        return datetime.combine(self.created_at.date(), time(23, 59, 59), tzinfo=timezone.utc)


class Token(Base):
    """The queue token issued for one encounter. Sequential per doctor, per
    calendar day (`token_date`) - the doctor's live queue (P3-F03+) is just
    this table filtered to today and ordered by `token_number`, not a
    separate stored entity."""

    __tablename__ = "opd_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opd_encounters.id"), nullable=False, unique=True
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False
    )

    token_date: Mapped[date_] = mapped_column(Date, nullable=False)
    token_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="WAITING")
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="NORMAL")

    called_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class Consultation(Base):
    """The doctor's clinical record for an encounter (P3-F05/P3-B04) - one
    row per encounter (`encounter_id` is unique), covering the standard OPD
    consultation sections: complaints, history, examination, diagnosis,
    allergies, vitals, investigation, treatment, and free-text notes."""

    __tablename__ = "opd_consultations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    encounter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opd_encounters.id"), nullable=False, unique=True
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False
    )

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="IN_PROGRESS")

    chief_complaint: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    history: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    examination: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    allergies: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    investigation: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    treatment: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    # Vitals - a fixed, structured set (unlike the free-text sections above)
    # since these are conventional discrete measurements, not prose.
    temperature_celsius: Mapped[float | None] = mapped_column(Numeric(4, 1), nullable=True)
    pulse_bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bp_systolic: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bp_diastolic: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spo2_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    respiratory_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Numeric(5, 1), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    encounter: Mapped["OPDEncounter"] = relationship(lazy="selectin")
    doctor: Mapped["Doctor"] = relationship(lazy="selectin")  # noqa: F821


class Prescription(Base):
    """The prescription issued for a consultation (P3-F06/P3-B05) - one per
    consultation (`consultation_id` is unique); `items` holds the medicine
    lines. `facility_id`/`doctor_id` are denormalized from the consultation
    so isolation/authorization checks don't require a join for every
    operation - see `app/modules/opd/service.py`."""

    __tablename__ = "opd_prescriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    facility_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("facilities.id"), nullable=False
    )
    consultation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opd_consultations.id"), nullable=False, unique=True
    )
    doctor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False
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

    items: Mapped[list["PrescriptionItem"]] = relationship(
        lazy="selectin", order_by="PrescriptionItem.created_at", cascade="all, delete-orphan"
    )
    consultation: Mapped["Consultation"] = relationship(lazy="selectin")
    doctor: Mapped["Doctor"] = relationship(lazy="selectin")  # noqa: F821


class PrescriptionItem(Base):
    """One medicine line (P3-F06: Medicine, Dosage, Route, Frequency,
    Duration, Instructions). Every field but `instructions` is required -
    enforced at the schema layer (`PrescriptionItemIn`), not here, since
    SQLAlchemy nullability alone can't express "required in the API but the
    column stays nullable for older/partial rows"."""

    __tablename__ = "opd_prescription_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prescription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("opd_prescriptions.id"), nullable=False
    )
    drug_name: Mapped[str] = mapped_column(String(255), nullable=False)
    dosage: Mapped[str] = mapped_column(String(100), nullable=False)
    route: Mapped[str] = mapped_column(String(30), nullable=False)
    frequency: Mapped[str] = mapped_column(String(100), nullable=False)
    duration: Mapped[str] = mapped_column(String(100), nullable=False)
    instructions: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
