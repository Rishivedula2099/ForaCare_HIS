import hashlib
import hmac
import re
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError, ConflictError, ForbiddenError, NotFoundError
from app.core.permissions import ensure_same_facility, ensure_same_tenant
from app.modules.audit import service as audit_service
from app.modules.auth.models import User
from app.modules.doctors.models import Doctor
from app.modules.facilities.models import Facility
from app.modules.lab.models import (
    Accession,
    Approval,
    LabOrder,
    LabOrderStatusHistory,
    Parameter,
    ReferenceRange,
    Result,
    ResultVersion,
    Sample,
    SampleStatus,
    Test,
    Verification,
)
from app.modules.lab.schemas import (
    AccessionCreateRequest,
    AccessionOut,
    ApprovalOut,
    BarcodeResolveResponse,
    LabOrderOut,
    LabOrderStatusHistoryOut,
    LabReportOut,
    LabReportVerifyOut,
    ParameterCreateRequest,
    ParameterOut,
    ParameterUpdateRequest,
    ReferenceRangeCreateRequest,
    ReferenceRangeOut,
    ReferenceRangeUpdateRequest,
    ReportResultRow,
    ResultEntryFieldOut,
    ResultEntryFormOut,
    ResultEntryRequest,
    ResultOut,
    ResultVersionOut,
    SampleCollectRequest,
    SampleOut,
    SampleStatusHistoryOut,
    TestCreateRequest,
    TestOut,
    TestUpdateRequest,
    validate_reference_range_ordering,
    VerificationOut,
)
from app.modules.patients.models import Patient


# ---------------------------------------------------------------------------
# Test (master)
# ---------------------------------------------------------------------------


async def list_tests(
    db: AsyncSession, current_user: User, *, name: str | None = None, is_active: bool | None = None
) -> list[TestOut]:
    stmt = select(Test).where(
        Test.tenant_id == current_user.tenant_id, Test.facility_id == current_user.facility_id
    )
    if name:
        stmt = stmt.where(Test.name.ilike(f"%{name}%"))
    if is_active is not None:
        stmt = stmt.where(Test.is_active == is_active)
    stmt = stmt.order_by(Test.name)

    result = await db.execute(stmt)
    return [TestOut.model_validate(test) for test in result.scalars().all()]


async def _get_test_or_404(db: AsyncSession, test_id: uuid.UUID) -> Test:
    result = await db.execute(select(Test).where(Test.id == test_id))
    test = result.scalar_one_or_none()
    if test is None:
        raise NotFoundError("Lab test not found.")
    return test


async def get_test(db: AsyncSession, test_id: uuid.UUID, current_user: User) -> TestOut:
    test = await _get_test_or_404(db, test_id)
    ensure_same_tenant(test.tenant_id, current_user)
    ensure_same_facility(test.facility_id, current_user)
    return TestOut.model_validate(test)


async def create_test(db: AsyncSession, payload: TestCreateRequest, current_user: User) -> TestOut:
    existing = await db.execute(
        select(Test).where(Test.facility_id == current_user.facility_id, Test.test_code == payload.test_code)
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A lab test with this code already exists in this facility.")

    test = Test(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        **payload.model_dump(),
    )
    db.add(test)
    await db.flush()

    await audit_service.record_event(
        db,
        action="lab.test_created",
        resource_type="lab_test",
        resource_id=test.id,
        after=TestOut.model_validate(test).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(test)
    return TestOut.model_validate(test)


async def update_test(
    db: AsyncSession, test_id: uuid.UUID, payload: TestUpdateRequest, current_user: User
) -> TestOut:
    test = await _get_test_or_404(db, test_id)
    ensure_same_tenant(test.tenant_id, current_user)
    ensure_same_facility(test.facility_id, current_user)

    before = TestOut.model_validate(test).model_dump(mode="json")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(test, field, value)
    await db.flush()

    await audit_service.record_event(
        db,
        action="lab.test_updated",
        resource_type="lab_test",
        resource_id=test.id,
        before=before,
        after=TestOut.model_validate(test).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(test)
    return TestOut.model_validate(test)


# ---------------------------------------------------------------------------
# Parameter (master, nested under Test)
# ---------------------------------------------------------------------------


async def list_parameters(db: AsyncSession, test_id: uuid.UUID, current_user: User) -> list[ParameterOut]:
    test = await _get_test_or_404(db, test_id)
    ensure_same_tenant(test.tenant_id, current_user)
    ensure_same_facility(test.facility_id, current_user)

    stmt = select(Parameter).where(Parameter.test_id == test_id).order_by(Parameter.sequence_order)
    result = await db.execute(stmt)
    return [ParameterOut.model_validate(parameter) for parameter in result.scalars().all()]


async def _get_parameter_or_404(db: AsyncSession, parameter_id: uuid.UUID) -> Parameter:
    result = await db.execute(select(Parameter).where(Parameter.id == parameter_id))
    parameter = result.scalar_one_or_none()
    if parameter is None:
        raise NotFoundError("Lab parameter not found.")
    return parameter


async def get_parameter(db: AsyncSession, parameter_id: uuid.UUID, current_user: User) -> ParameterOut:
    parameter = await _get_parameter_or_404(db, parameter_id)
    ensure_same_tenant(parameter.tenant_id, current_user)
    ensure_same_facility(parameter.facility_id, current_user)
    return ParameterOut.model_validate(parameter)


async def create_parameter(
    db: AsyncSession, test_id: uuid.UUID, payload: ParameterCreateRequest, current_user: User
) -> ParameterOut:
    test = await _get_test_or_404(db, test_id)
    ensure_same_tenant(test.tenant_id, current_user)
    ensure_same_facility(test.facility_id, current_user)

    existing = await db.execute(
        select(Parameter).where(
            Parameter.test_id == test_id, Parameter.parameter_code == payload.parameter_code
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A parameter with this code already exists for this test.")

    parameter = Parameter(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        test_id=test_id,
        **payload.model_dump(),
    )
    db.add(parameter)
    await db.flush()

    await audit_service.record_event(
        db,
        action="lab.parameter_created",
        resource_type="lab_parameter",
        resource_id=parameter.id,
        after=ParameterOut.model_validate(parameter).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(parameter)
    return ParameterOut.model_validate(parameter)


async def update_parameter(
    db: AsyncSession, parameter_id: uuid.UUID, payload: ParameterUpdateRequest, current_user: User
) -> ParameterOut:
    parameter = await _get_parameter_or_404(db, parameter_id)
    ensure_same_tenant(parameter.tenant_id, current_user)
    ensure_same_facility(parameter.facility_id, current_user)

    before = ParameterOut.model_validate(parameter).model_dump(mode="json")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(parameter, field, value)
    await db.flush()

    await audit_service.record_event(
        db,
        action="lab.parameter_updated",
        resource_type="lab_parameter",
        resource_id=parameter.id,
        before=before,
        after=ParameterOut.model_validate(parameter).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(parameter)
    return ParameterOut.model_validate(parameter)


# ---------------------------------------------------------------------------
# ReferenceRange (master, nested under Parameter)
# ---------------------------------------------------------------------------


async def list_reference_ranges(
    db: AsyncSession, parameter_id: uuid.UUID, current_user: User
) -> list[ReferenceRangeOut]:
    parameter = await _get_parameter_or_404(db, parameter_id)
    ensure_same_tenant(parameter.tenant_id, current_user)
    ensure_same_facility(parameter.facility_id, current_user)

    stmt = (
        select(ReferenceRange)
        .where(ReferenceRange.parameter_id == parameter_id)
        .order_by(ReferenceRange.gender, ReferenceRange.age_min_days)
    )
    result = await db.execute(stmt)
    return [ReferenceRangeOut.model_validate(item) for item in result.scalars().all()]


async def _get_reference_range_or_404(db: AsyncSession, reference_range_id: uuid.UUID) -> ReferenceRange:
    result = await db.execute(select(ReferenceRange).where(ReferenceRange.id == reference_range_id))
    reference_range = result.scalar_one_or_none()
    if reference_range is None:
        raise NotFoundError("Reference range not found.")
    return reference_range


async def create_reference_range(
    db: AsyncSession,
    parameter_id: uuid.UUID,
    payload: ReferenceRangeCreateRequest,
    current_user: User,
) -> ReferenceRangeOut:
    parameter = await _get_parameter_or_404(db, parameter_id)
    ensure_same_tenant(parameter.tenant_id, current_user)
    ensure_same_facility(parameter.facility_id, current_user)

    reference_range = ReferenceRange(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        parameter_id=parameter_id,
        **payload.model_dump(),
    )
    db.add(reference_range)
    await db.flush()

    await audit_service.record_event(
        db,
        action="lab.reference_range_created",
        resource_type="lab_reference_range",
        resource_id=reference_range.id,
        after=ReferenceRangeOut.model_validate(reference_range).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(reference_range)
    return ReferenceRangeOut.model_validate(reference_range)


async def update_reference_range(
    db: AsyncSession,
    reference_range_id: uuid.UUID,
    payload: ReferenceRangeUpdateRequest,
    current_user: User,
) -> ReferenceRangeOut:
    reference_range = await _get_reference_range_or_404(db, reference_range_id)
    ensure_same_tenant(reference_range.tenant_id, current_user)
    ensure_same_facility(reference_range.facility_id, current_user)

    before = ReferenceRangeOut.model_validate(reference_range).model_dump(mode="json")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(reference_range, field, value)

    # A partial PATCH only carries the fields that changed, but the
    # critical_low < normal_min < normal_max < critical_high rule spans all
    # four - re-validate against the merged row, not just the payload.
    validate_reference_range_ordering(
        reference_range.critical_low,
        reference_range.normal_min,
        reference_range.normal_max,
        reference_range.critical_high,
    )
    await db.flush()

    await audit_service.record_event(
        db,
        action="lab.reference_range_updated",
        resource_type="lab_reference_range",
        resource_id=reference_range.id,
        before=before,
        after=ReferenceRangeOut.model_validate(reference_range).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(reference_range)
    return ReferenceRangeOut.model_validate(reference_range)


# ---------------------------------------------------------------------------
# LabOrder (P6-B02 state machine)
# ---------------------------------------------------------------------------

# The lab order state machine (P6-B02). Every transition goes through
# `transition_lab_order_status`, which is the only place that may write
# `LabOrder.status` - so this map is a complete description of what's
# reachable from where. TECHNICALLY_VERIFIED/PENDING_APPROVAL can send an
# order back to RESULT_ENTERED (a failed technical verification or a
# pathologist rejection); APPROVED/FINALIZED are otherwise a straight line.
# CANCELLED is reachable from every non-terminal state.
LAB_ORDER_TRANSITIONS: dict[str, set[str]] = {
    "ORDERED": {"BILLED", "CANCELLED"},
    "BILLED": {"ACCESSIONED", "CANCELLED"},
    "ACCESSIONED": {"COLLECTION_PENDING", "CANCELLED"},
    "COLLECTION_PENDING": {"COLLECTED", "CANCELLED"},
    "COLLECTED": {"PROCESSING", "CANCELLED"},
    "PROCESSING": {"RESULT_ENTERED", "CANCELLED"},
    "RESULT_ENTERED": {"TECHNICALLY_VERIFIED", "CANCELLED"},
    "TECHNICALLY_VERIFIED": {"PENDING_APPROVAL", "RESULT_ENTERED", "CANCELLED"},
    "PENDING_APPROVAL": {"APPROVED", "RESULT_ENTERED", "CANCELLED"},
    "APPROVED": {"FINALIZED"},
    "FINALIZED": set(),
    "CANCELLED": set(),
}

# Which permission a caller needs to move an order *into* a given status -
# mirrors the per-stage permissions already in `rbac.constants.PERMISSION_CATALOG`
# (`lab.accession_sample`/`lab.enter_results`/`lab.verify_results`/
# `lab.approve_reports`) rather than gating the whole machine behind one
# blanket permission, since each stage is owned by a different role
# (LAB_TECH vs LAB_APPROVER).
LAB_ORDER_TRANSITION_PERMISSIONS: dict[str, str] = {
    "BILLED": "billing.invoice.create",
    "ACCESSIONED": "lab.accession_sample",
    "COLLECTION_PENDING": "lab.accession_sample",
    "COLLECTED": "lab.accession_sample",
    "PROCESSING": "lab.enter_results",
    "RESULT_ENTERED": "lab.enter_results",
    "TECHNICALLY_VERIFIED": "lab.verify_results",
    "PENDING_APPROVAL": "lab.verify_results",
    "APPROVED": "lab.approve_reports",
    "FINALIZED": "lab.approve_reports",
    "CANCELLED": "lab.approve_reports",
}


def _ensure_can_transition_to(current_user: User, new_status: str, *, required_permission: str | None = None) -> None:
    needed = required_permission if required_permission is not None else LAB_ORDER_TRANSITION_PERMISSIONS[new_status]
    user_permission_codes = {permission.code for permission in current_user.role.permissions}
    if needed not in user_permission_codes:
        raise ForbiddenError("You do not have permission to perform this action.")


async def _get_lab_order_or_404(db: AsyncSession, lab_order_id: uuid.UUID) -> LabOrder:
    result = await db.execute(select(LabOrder).where(LabOrder.id == lab_order_id))
    lab_order = result.scalar_one_or_none()
    if lab_order is None:
        raise NotFoundError("Lab order not found.")
    return lab_order


async def get_lab_order(db: AsyncSession, lab_order_id: uuid.UUID, current_user: User) -> LabOrderOut:
    lab_order = await _get_lab_order_or_404(db, lab_order_id)
    ensure_same_tenant(lab_order.tenant_id, current_user)
    ensure_same_facility(lab_order.facility_id, current_user)
    return LabOrderOut.model_validate(lab_order)


async def list_lab_orders(
    db: AsyncSession,
    current_user: User,
    *,
    patient_id: uuid.UUID | None = None,
    status: str | None = None,
    accession_id: uuid.UUID | None = None,
) -> list[LabOrderOut]:
    stmt = select(LabOrder).where(
        LabOrder.tenant_id == current_user.tenant_id, LabOrder.facility_id == current_user.facility_id
    )
    if patient_id is not None:
        stmt = stmt.where(LabOrder.patient_id == patient_id)
    if status is not None:
        stmt = stmt.where(LabOrder.status == status)
    if accession_id is not None:
        stmt = stmt.where(LabOrder.accession_id == accession_id)
    stmt = stmt.order_by(LabOrder.ordered_at)

    result = await db.execute(stmt)
    return [LabOrderOut.model_validate(order) for order in result.scalars().all()]


async def list_lab_order_status_history(
    db: AsyncSession, lab_order_id: uuid.UUID, current_user: User
) -> list[LabOrderStatusHistoryOut]:
    lab_order = await _get_lab_order_or_404(db, lab_order_id)
    ensure_same_tenant(lab_order.tenant_id, current_user)
    ensure_same_facility(lab_order.facility_id, current_user)

    stmt = (
        select(LabOrderStatusHistory)
        .where(LabOrderStatusHistory.lab_order_id == lab_order_id)
        .order_by(LabOrderStatusHistory.changed_at)
    )
    result = await db.execute(stmt)
    return [LabOrderStatusHistoryOut.model_validate(row) for row in result.scalars().all()]


async def transition_lab_order_status(
    db: AsyncSession,
    current_user: User,
    lab_order_id: uuid.UUID,
    new_status: str,
    *,
    remarks: str | None = None,
    required_permission: str | None = None,
) -> LabOrderOut:
    """`required_permission` overrides the default per-target-status lookup
    in `LAB_ORDER_TRANSITION_PERMISSIONS` - needed because a handful of
    targets are reachable from more than one direction by different roles
    (e.g. RESULT_ENTERED is both the tech's forward entry point, gated on
    `lab.enter_results`, and where a verifier/approver sends a flawed order
    back from, gated on their own permission instead)."""
    result = await db.execute(select(LabOrder).where(LabOrder.id == lab_order_id).with_for_update())
    lab_order = result.scalar_one_or_none()
    if lab_order is None:
        raise NotFoundError("Lab order not found.")
    ensure_same_tenant(lab_order.tenant_id, current_user)
    ensure_same_facility(lab_order.facility_id, current_user)

    if new_status not in LAB_ORDER_TRANSITIONS:
        raise AppError(f"Unknown lab order status: {new_status}.", code="VALIDATION_ERROR")

    allowed_next = LAB_ORDER_TRANSITIONS[lab_order.status]
    if new_status not in allowed_next:
        raise AppError(
            f"Cannot move a lab order from {lab_order.status} to {new_status}.",
            code="INVALID_TRANSITION",
        )

    _ensure_can_transition_to(current_user, new_status, required_permission=required_permission)

    before_status = lab_order.status
    lab_order.status = new_status
    lab_order.updated_at = datetime.now(timezone.utc)
    await db.flush()

    history_row = LabOrderStatusHistory(
        tenant_id=lab_order.tenant_id,
        facility_id=lab_order.facility_id,
        lab_order_id=lab_order.id,
        changed_by=current_user.id,
        status=new_status,
        remarks=remarks,
    )
    db.add(history_row)

    await audit_service.record_event(
        db,
        action="lab.order_status_changed",
        resource_type="lab_order",
        resource_id=lab_order.id,
        before={"status": before_status},
        after={"status": lab_order.status},
        commit=False,
    )
    await db.commit()
    await db.refresh(lab_order)
    return LabOrderOut.model_validate(lab_order)


# ---------------------------------------------------------------------------
# Accession / Sample (P6-B03 barcode generation, validation, resolution)
# ---------------------------------------------------------------------------

# `Accession.accession_number` (`LAB-YYMMDD-NNNN`, docs/requirements.md SS4.5)
# and `Sample.barcode_id` (`<accession_number>-NN`, one suffix per tube under
# that accession) - a scanned code matches exactly one of these two shapes,
# which is what `resolve_barcode` uses to decide which table to look in.
ACCESSION_NUMBER_PATTERN = re.compile(r"^LAB-\d{6}-\d{4}$")
SAMPLE_BARCODE_PATTERN = re.compile(r"^LAB-\d{6}-\d{4}-\d{2}$")


async def _lock_number_sequence(db: AsyncSession, key: str) -> None:
    """Transaction-scoped advisory lock (auto-released on commit/rollback),
    same mechanism as `opd._lock_doctor_queue`/`billing._lock_number_sequence`
    - needed because the first accession/sample of the day/accession has no
    row yet to `SELECT ... FOR UPDATE`."""
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:key))"), {"key": key})


async def _generate_accession_number(db: AsyncSession, current_user: User) -> str:
    today = datetime.now(timezone.utc).date()
    await _lock_number_sequence(db, f"lab-accession-number:{current_user.facility_id}:{today.isoformat()}")

    result = await db.execute(
        select(func.count())
        .select_from(Accession)
        .where(
            Accession.facility_id == current_user.facility_id,
            func.date(Accession.accessioned_at) == today,
        )
    )
    sequence = (result.scalar_one() or 0) + 1
    return f"LAB-{today.strftime('%y%m%d')}-{sequence:04d}"


async def _generate_sample_barcode(db: AsyncSession, accession: Accession) -> str:
    await _lock_number_sequence(db, f"lab-sample-barcode:{accession.id}")

    result = await db.execute(select(func.count()).select_from(Sample).where(Sample.accession_id == accession.id))
    tube_sequence = (result.scalar_one() or 0) + 1
    return f"{accession.accession_number}-{tube_sequence:02d}"


async def create_accession(db: AsyncSession, current_user: User, payload: AccessionCreateRequest) -> AccessionOut:
    order_ids = set(payload.lab_order_ids)
    result = await db.execute(
        select(LabOrder).where(LabOrder.id.in_(order_ids)).order_by(LabOrder.id).with_for_update()
    )
    orders = result.scalars().all()
    if len(orders) != len(order_ids):
        raise NotFoundError("One or more lab orders not found.")

    for order in orders:
        ensure_same_tenant(order.tenant_id, current_user)
        ensure_same_facility(order.facility_id, current_user)
        if order.patient_id != payload.patient_id:
            raise AppError(
                "All lab orders in an accession must belong to the same patient.", code="VALIDATION_ERROR"
            )
        if order.status != "BILLED":
            raise AppError(
                f"Lab order {order.order_number} must be BILLED before it can be accessioned "
                f"(currently {order.status}).",
                code="INVALID_TRANSITION",
            )

    accession_number = await _generate_accession_number(db, current_user)
    accession = Accession(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        patient_id=payload.patient_id,
        accessioned_by=current_user.id,
        accession_number=accession_number,
    )
    db.add(accession)
    await db.flush()

    for order in orders:
        order.accession_id = accession.id

    await audit_service.record_event(
        db,
        action="lab.accession_created",
        resource_type="lab_accession",
        resource_id=accession.id,
        after=AccessionOut.model_validate(accession).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(accession)

    for order in orders:
        await transition_lab_order_status(db, current_user, order.id, "ACCESSIONED")

    return AccessionOut.model_validate(accession)


async def _get_accession_or_404(db: AsyncSession, accession_id: uuid.UUID) -> Accession:
    result = await db.execute(select(Accession).where(Accession.id == accession_id))
    accession = result.scalar_one_or_none()
    if accession is None:
        raise NotFoundError("Accession not found.")
    return accession


async def get_accession(db: AsyncSession, accession_id: uuid.UUID, current_user: User) -> AccessionOut:
    accession = await _get_accession_or_404(db, accession_id)
    ensure_same_tenant(accession.tenant_id, current_user)
    ensure_same_facility(accession.facility_id, current_user)
    return AccessionOut.model_validate(accession)


async def collect_sample(
    db: AsyncSession, current_user: User, accession_id: uuid.UUID, payload: SampleCollectRequest
) -> SampleOut:
    result = await db.execute(select(Accession).where(Accession.id == accession_id).with_for_update())
    accession = result.scalar_one_or_none()
    if accession is None:
        raise NotFoundError("Accession not found.")
    ensure_same_tenant(accession.tenant_id, current_user)
    ensure_same_facility(accession.facility_id, current_user)

    order_ids = set(payload.lab_order_ids)
    order_result = await db.execute(select(LabOrder).where(LabOrder.id.in_(order_ids)).with_for_update())
    orders = order_result.scalars().all()
    if len(orders) != len(order_ids):
        raise NotFoundError("One or more lab orders not found.")

    for order in orders:
        if order.accession_id != accession.id:
            raise AppError(
                f"Lab order {order.order_number} does not belong to this accession.", code="VALIDATION_ERROR"
            )
        if order.status not in ("ACCESSIONED", "COLLECTION_PENDING"):
            raise AppError(
                f"Lab order {order.order_number} is not awaiting sample collection (currently {order.status}).",
                code="INVALID_TRANSITION",
            )

    barcode_id = await _generate_sample_barcode(db, accession)
    sample = Sample(
        tenant_id=accession.tenant_id,
        facility_id=accession.facility_id,
        accession_id=accession.id,
        barcode_id=barcode_id,
        specimen_type=payload.specimen_type,
        container_type=payload.container_type,
    )
    db.add(sample)
    await db.flush()

    for order in orders:
        order.sample_id = sample.id

    db.add(
        SampleStatus(
            tenant_id=sample.tenant_id,
            facility_id=sample.facility_id,
            sample_id=sample.id,
            changed_by=current_user.id,
            status=sample.status,
        )
    )

    await audit_service.record_event(
        db,
        action="lab.sample_created",
        resource_type="lab_sample",
        resource_id=sample.id,
        after=SampleOut.model_validate(sample).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(sample)

    for order in orders:
        if order.status == "ACCESSIONED":
            await transition_lab_order_status(db, current_user, order.id, "COLLECTION_PENDING")

    return SampleOut.model_validate(sample)


async def _get_sample_or_404(db: AsyncSession, sample_id: uuid.UUID) -> Sample:
    result = await db.execute(select(Sample).where(Sample.id == sample_id))
    sample = result.scalar_one_or_none()
    if sample is None:
        raise NotFoundError("Sample not found.")
    return sample


async def get_sample(db: AsyncSession, sample_id: uuid.UUID, current_user: User) -> SampleOut:
    sample = await _get_sample_or_404(db, sample_id)
    ensure_same_tenant(sample.tenant_id, current_user)
    ensure_same_facility(sample.facility_id, current_user)
    return SampleOut.model_validate(sample)


# The sample state machine (P6-B04). Every transition goes through
# `transition_sample_status`, which is the only place that may write
# `Sample.status` - mirrors `LAB_ORDER_TRANSITIONS` above. IN_TRANSIT/RECEIVED
# distinguish "handed to a courier" from "received at the testing lab" for a
# facility that ships tubes out; a same-site lab can skip straight from
# COLLECTED to RECEIVED (`process_sample` does exactly that). REJECTED is
# reachable any time before the sample is fully RECEIVED.
SAMPLE_TRANSITIONS: dict[str, set[str]] = {
    "PENDING_COLLECTION": {"COLLECTED", "REJECTED"},
    "COLLECTED": {"IN_TRANSIT", "RECEIVED", "REJECTED"},
    "IN_TRANSIT": {"RECEIVED", "REJECTED"},
    "RECEIVED": set(),
    "REJECTED": set(),
}

# Each transition is gated by `lab.accession_sample` (the same permission
# that creates accessions/tubes) - sample handling is one continuous
# LAB_TECH workflow, unlike the LabOrder machine where different stages
# belong to different roles.
_SAMPLE_TRANSITION_PERMISSION = "lab.accession_sample"

# Which LabOrder transition a sample transition cascades into, for every
# order currently pointed at this sample (`LabOrder.sample_id`) - keeps
# `LabOrder.status` and `Sample.status` in lockstep without the caller having
# to drive both machines by hand.
_SAMPLE_TO_ORDER_CASCADE: dict[str, tuple[str, str]] = {
    "COLLECTED": ("COLLECTION_PENDING", "COLLECTED"),
    "RECEIVED": ("COLLECTED", "PROCESSING"),
}


async def transition_sample_status(
    db: AsyncSession,
    current_user: User,
    sample_id: uuid.UUID,
    new_status: str,
    *,
    remarks: str | None = None,
) -> SampleOut:
    result = await db.execute(select(Sample).where(Sample.id == sample_id).with_for_update())
    sample = result.scalar_one_or_none()
    if sample is None:
        raise NotFoundError("Sample not found.")
    ensure_same_tenant(sample.tenant_id, current_user)
    ensure_same_facility(sample.facility_id, current_user)

    if new_status not in SAMPLE_TRANSITIONS:
        raise AppError(f"Unknown sample status: {new_status}.", code="VALIDATION_ERROR")

    allowed_next = SAMPLE_TRANSITIONS[sample.status]
    if new_status not in allowed_next:
        raise AppError(
            f"Cannot move a sample from {sample.status} to {new_status}.", code="INVALID_TRANSITION"
        )

    if new_status == "REJECTED" and not (remarks and remarks.strip()):
        raise AppError("A rejection reason is required.", code="VALIDATION_ERROR")

    user_permission_codes = {permission.code for permission in current_user.role.permissions}
    if _SAMPLE_TRANSITION_PERMISSION not in user_permission_codes:
        raise ForbiddenError("You do not have permission to perform this action.")

    sample.status = new_status
    if new_status == "COLLECTED":
        sample.collected_by = current_user.id
        sample.collected_at = datetime.now(timezone.utc)
    elif new_status == "REJECTED":
        sample.rejection_reason = remarks
    await db.flush()

    db.add(
        SampleStatus(
            tenant_id=sample.tenant_id,
            facility_id=sample.facility_id,
            sample_id=sample.id,
            changed_by=current_user.id,
            status=sample.status,
            remarks=remarks,
        )
    )

    await audit_service.record_event(
        db,
        action="lab.sample_status_changed",
        resource_type="lab_sample",
        resource_id=sample.id,
        after=SampleOut.model_validate(sample).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(sample)

    cascade = _SAMPLE_TO_ORDER_CASCADE.get(new_status)
    if cascade is not None:
        from_status, to_status = cascade
        orders_result = await db.execute(select(LabOrder).where(LabOrder.sample_id == sample.id))
        for order in orders_result.scalars().all():
            if order.status == from_status:
                await transition_lab_order_status(db, current_user, order.id, to_status)

    return SampleOut.model_validate(sample)


async def mark_sample_collected(
    db: AsyncSession, current_user: User, sample_id: uuid.UUID, *, remarks: str | None = None
) -> SampleOut:
    return await transition_sample_status(db, current_user, sample_id, "COLLECTED", remarks=remarks)


async def reject_sample(
    db: AsyncSession, current_user: User, sample_id: uuid.UUID, *, reason: str
) -> SampleOut:
    return await transition_sample_status(db, current_user, sample_id, "REJECTED", remarks=reason)


async def process_sample(db: AsyncSession, current_user: User, sample_id: uuid.UUID) -> SampleOut:
    """Marks a sample RECEIVED at the testing lab (P6-B04 "Process sample")
    and cascades its orders COLLECTED -> PROCESSING. A facility that ships
    tubes out can first move through IN_TRANSIT via
    `transition_sample_status` directly; this is the common same-site path
    straight from COLLECTED."""
    return await transition_sample_status(db, current_user, sample_id, "RECEIVED")


async def list_sample_status_history(
    db: AsyncSession, sample_id: uuid.UUID, current_user: User
) -> list[SampleStatusHistoryOut]:
    sample = await _get_sample_or_404(db, sample_id)
    ensure_same_tenant(sample.tenant_id, current_user)
    ensure_same_facility(sample.facility_id, current_user)

    stmt = (
        select(SampleStatus).where(SampleStatus.sample_id == sample_id).order_by(SampleStatus.changed_at)
    )
    result = await db.execute(stmt)
    return [SampleStatusHistoryOut.model_validate(row) for row in result.scalars().all()]


async def resolve_barcode(db: AsyncSession, current_user: User, code: str) -> BarcodeResolveResponse:
    """Scan-workflow lookup (P6-F03): resolves a scanned tube/accession label
    back to its record and the lab orders riding on it. `SAMPLE_BARCODE_PATTERN`
    is checked first since every sample barcode is an accession number plus a
    tube suffix, so it would also satisfy a looser accession check."""
    code = code.strip().upper()

    if SAMPLE_BARCODE_PATTERN.match(code):
        result = await db.execute(select(Sample).where(Sample.barcode_id == code))
        sample = result.scalar_one_or_none()
        if sample is None:
            raise NotFoundError("No sample found for this barcode.")
        ensure_same_tenant(sample.tenant_id, current_user)
        ensure_same_facility(sample.facility_id, current_user)

        accession = await _get_accession_or_404(db, sample.accession_id)
        orders_result = await db.execute(select(LabOrder).where(LabOrder.sample_id == sample.id))
        return BarcodeResolveResponse(
            code_type="SAMPLE",
            accession=AccessionOut.model_validate(accession),
            sample=SampleOut.model_validate(sample),
            lab_orders=[LabOrderOut.model_validate(order) for order in orders_result.scalars().all()],
        )

    if ACCESSION_NUMBER_PATTERN.match(code):
        result = await db.execute(select(Accession).where(Accession.accession_number == code))
        accession = result.scalar_one_or_none()
        if accession is None:
            raise NotFoundError("No accession found for this barcode.")
        ensure_same_tenant(accession.tenant_id, current_user)
        ensure_same_facility(accession.facility_id, current_user)

        orders_result = await db.execute(select(LabOrder).where(LabOrder.accession_id == accession.id))
        return BarcodeResolveResponse(
            code_type="ACCESSION",
            accession=AccessionOut.model_validate(accession),
            sample=None,
            lab_orders=[LabOrderOut.model_validate(order) for order in orders_result.scalars().all()],
        )

    raise AppError("Not a recognized lab barcode format.", code="VALIDATION_ERROR")


# ---------------------------------------------------------------------------
# Result (P6-B05 result engine / P6-F05 result entry)
# ---------------------------------------------------------------------------


def _resolve_reference_range(
    parameter: Parameter, patient: Patient, as_of: date
) -> ReferenceRange | None:
    """Picks the band that applies to this patient (`docs/masters.md` SS3.3:
    gender + age-in-days banded ranges) - prefers a gender-specific row over
    an `ALL` one when both match the same age band, since `ALL` is the
    fallback a master-data editor uses when no sex-specific values are
    known."""
    age_days = (as_of - patient.dob).days
    candidates = [
        reference_range
        for reference_range in parameter.reference_ranges
        if reference_range.age_min_days <= age_days
        and (reference_range.age_max_days is None or age_days <= reference_range.age_max_days)
        and reference_range.gender in ("ALL", patient.gender)
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda reference_range: 0 if reference_range.gender != "ALL" else 1)
    return candidates[0]


def _calculate_flag(value: str, reference_range: ReferenceRange | None) -> str:
    """LOW/NORMAL/HIGH/CRITICAL (`docs/requirements.md` SS4.5) - a critical
    bound always wins over a merely-out-of-range one. A non-numeric value
    (qualitative results like "Reactive"/"Nil") or a parameter with no
    matching reference range can't be auto-flagged, so it reads NORMAL
    rather than guessing."""
    if reference_range is None:
        return "NORMAL"
    try:
        numeric_value = float(value)
    except ValueError:
        return "NORMAL"

    if reference_range.critical_low is not None and numeric_value < float(reference_range.critical_low):
        return "CRITICAL"
    if reference_range.critical_high is not None and numeric_value > float(reference_range.critical_high):
        return "CRITICAL"
    if numeric_value < float(reference_range.normal_min):
        return "LOW"
    if numeric_value > float(reference_range.normal_max):
        return "HIGH"
    return "NORMAL"


async def _get_patient_or_404(db: AsyncSession, patient_id: uuid.UUID) -> Patient:
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if patient is None:
        raise NotFoundError("Patient not found.")
    return patient


async def get_result_entry_form(
    db: AsyncSession, current_user: User, lab_order_id: uuid.UUID
) -> ResultEntryFormOut:
    lab_order = await _get_lab_order_or_404(db, lab_order_id)
    ensure_same_tenant(lab_order.tenant_id, current_user)
    ensure_same_facility(lab_order.facility_id, current_user)

    test = await _get_test_or_404(db, lab_order.test_id)
    patient = await _get_patient_or_404(db, lab_order.patient_id)
    today = datetime.now(timezone.utc).date()

    existing_result = await db.execute(select(Result).where(Result.lab_order_id == lab_order_id))
    existing_by_parameter = {row.parameter_id: row for row in existing_result.scalars().all()}

    fields: list[ResultEntryFieldOut] = []
    for parameter in test.parameters:
        if not parameter.is_active:
            continue
        reference_range = _resolve_reference_range(parameter, patient, today)
        existing = existing_by_parameter.get(parameter.id)
        fields.append(
            ResultEntryFieldOut(
                parameter_id=parameter.id,
                parameter_code=parameter.parameter_code,
                name=parameter.name,
                unit=parameter.unit,
                normal_min=float(reference_range.normal_min) if reference_range else None,
                normal_max=float(reference_range.normal_max) if reference_range else None,
                critical_low=float(reference_range.critical_low)
                if reference_range and reference_range.critical_low is not None
                else None,
                critical_high=float(reference_range.critical_high)
                if reference_range and reference_range.critical_high is not None
                else None,
                value=existing.value if existing else None,
                flag=existing.flag if existing else None,
            )
        )

    return ResultEntryFormOut(
        lab_order_id=lab_order.id,
        order_number=lab_order.order_number,
        order_status=lab_order.status,
        test_name=test.name,
        fields=fields,
    )


async def enter_results(
    db: AsyncSession, current_user: User, lab_order_id: uuid.UUID, payload: ResultEntryRequest
) -> list[ResultOut]:
    result = await db.execute(select(LabOrder).where(LabOrder.id == lab_order_id).with_for_update())
    lab_order = result.scalar_one_or_none()
    if lab_order is None:
        raise NotFoundError("Lab order not found.")
    ensure_same_tenant(lab_order.tenant_id, current_user)
    ensure_same_facility(lab_order.facility_id, current_user)

    if lab_order.status != "PROCESSING":
        raise AppError(
            f"Results can only be entered while the order is PROCESSING (currently {lab_order.status}).",
            code="INVALID_TRANSITION",
        )

    test = await _get_test_or_404(db, lab_order.test_id)
    parameters_by_id = {parameter.id: parameter for parameter in test.parameters if parameter.is_active}

    submitted_ids = {item.parameter_id for item in payload.items}
    unknown_ids = submitted_ids - parameters_by_id.keys()
    if unknown_ids:
        raise AppError(
            "One or more parameters do not belong to this test.", code="VALIDATION_ERROR"
        )
    missing_ids = parameters_by_id.keys() - submitted_ids
    if missing_ids:
        raise AppError(
            "A value is required for every parameter of this test.", code="VALIDATION_ERROR"
        )

    patient = await _get_patient_or_404(db, lab_order.patient_id)
    today = datetime.now(timezone.utc).date()

    saved_rows: list[Result] = []
    for item in payload.items:
        parameter = parameters_by_id[item.parameter_id]

        # Unit validation: a caller-supplied unit must match the parameter's
        # master-data unit when one is defined; otherwise the parameter's
        # unit is used as-is.
        unit = item.unit.strip() if item.unit else parameter.unit
        if parameter.unit and item.unit and item.unit.strip().lower() != parameter.unit.strip().lower():
            raise AppError(
                f"Unit for {parameter.name} must be {parameter.unit}.", code="VALIDATION_ERROR"
            )

        reference_range = _resolve_reference_range(parameter, patient, today)
        flag = _calculate_flag(item.value, reference_range)

        existing_result = await db.execute(
            select(Result)
            .where(Result.lab_order_id == lab_order.id, Result.parameter_id == parameter.id)
            .with_for_update()
        )
        row = existing_result.scalar_one_or_none()
        if row is None:
            row = Result(
                tenant_id=lab_order.tenant_id,
                facility_id=lab_order.facility_id,
                lab_order_id=lab_order.id,
                parameter_id=parameter.id,
                sample_id=lab_order.sample_id,
                entered_by=current_user.id,
                value=item.value,
                unit=unit,
                flag=flag,
            )
            db.add(row)
            await db.flush()
            version_number = 1
        else:
            row.value = item.value
            row.unit = unit
            row.flag = flag
            row.entered_by = current_user.id
            row.entered_at = datetime.now(timezone.utc)
            row.current_version += 1
            await db.flush()
            version_number = row.current_version

        db.add(
            ResultVersion(
                tenant_id=row.tenant_id,
                facility_id=row.facility_id,
                result_id=row.id,
                changed_by=current_user.id,
                version_number=version_number,
                value=row.value,
                flag=row.flag,
            )
        )
        saved_rows.append(row)

    await audit_service.record_event(
        db,
        action="lab.results_entered",
        resource_type="lab_order",
        resource_id=lab_order.id,
        after={
            "parameter_count": len(saved_rows),
            "critical_count": sum(1 for row in saved_rows if row.flag == "CRITICAL"),
        },
        commit=False,
    )
    await db.commit()
    for row in saved_rows:
        await db.refresh(row)

    await transition_lab_order_status(db, current_user, lab_order.id, "RESULT_ENTERED")

    return [ResultOut.model_validate(row) for row in saved_rows]


async def list_results(db: AsyncSession, current_user: User, lab_order_id: uuid.UUID) -> list[ResultOut]:
    lab_order = await _get_lab_order_or_404(db, lab_order_id)
    ensure_same_tenant(lab_order.tenant_id, current_user)
    ensure_same_facility(lab_order.facility_id, current_user)

    result = await db.execute(select(Result).where(Result.lab_order_id == lab_order_id))
    return [ResultOut.model_validate(row) for row in result.scalars().all()]


async def _get_result_or_404(db: AsyncSession, result_id: uuid.UUID) -> Result:
    result = await db.execute(select(Result).where(Result.id == result_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError("Result not found.")
    return row


async def list_result_versions(
    db: AsyncSession, current_user: User, result_id: uuid.UUID
) -> list[ResultVersionOut]:
    row = await _get_result_or_404(db, result_id)
    ensure_same_tenant(row.tenant_id, current_user)
    ensure_same_facility(row.facility_id, current_user)

    stmt = (
        select(ResultVersion)
        .where(ResultVersion.result_id == result_id)
        .order_by(ResultVersion.version_number)
    )
    result = await db.execute(stmt)
    return [ResultVersionOut.model_validate(version) for version in result.scalars().all()]


async def amend_result(
    db: AsyncSession,
    current_user: User,
    result_id: uuid.UUID,
    *,
    value: str,
    unit: str | None,
    reason: str,
) -> ResultOut:
    """P6-B06: the only codepath that may change a `Result` once its
    `LabOrder` has passed approval - everywhere else (`enter_results`) is
    gated to the `PROCESSING`/`RESULT_ENTERED` stage, before anything has
    been approved, so this is deliberately the single place a *silent*
    overwrite of an approved result could happen without the mandatory
    `reason` and version bump this enforces."""
    result = await db.execute(select(Result).where(Result.id == result_id).with_for_update())
    row = result.scalar_one_or_none()
    if row is None:
        raise NotFoundError("Result not found.")
    ensure_same_tenant(row.tenant_id, current_user)
    ensure_same_facility(row.facility_id, current_user)

    lab_order = await _get_lab_order_or_404(db, row.lab_order_id)
    if lab_order.status not in ("APPROVED", "FINALIZED"):
        raise AppError(
            "Only a result on an APPROVED or FINALIZED order can be amended; "
            "re-enter it normally while the order is still being processed.",
            code="INVALID_TRANSITION",
        )

    user_permission_codes = {permission.code for permission in current_user.role.permissions}
    if "lab.approve_reports" not in user_permission_codes:
        raise ForbiddenError("You do not have permission to perform this action.")

    parameter = await _get_parameter_or_404(db, row.parameter_id)
    patient = await _get_patient_or_404(db, lab_order.patient_id)
    today = datetime.now(timezone.utc).date()
    reference_range = _resolve_reference_range(parameter, patient, today)

    row.value = value
    row.unit = unit or parameter.unit
    row.flag = _calculate_flag(value, reference_range)
    row.status = "AMENDED"
    row.current_version += 1
    row.entered_by = current_user.id
    row.entered_at = datetime.now(timezone.utc)
    await db.flush()

    db.add(
        ResultVersion(
            tenant_id=row.tenant_id,
            facility_id=row.facility_id,
            result_id=row.id,
            changed_by=current_user.id,
            version_number=row.current_version,
            value=row.value,
            flag=row.flag,
            change_reason=reason,
        )
    )

    await audit_service.record_event(
        db,
        action="lab.result_amended",
        resource_type="lab_result",
        resource_id=row.id,
        after={"value": row.value, "flag": row.flag, "reason": reason, "version": row.current_version},
        commit=False,
    )
    await db.commit()
    await db.refresh(row)
    return ResultOut.model_validate(row)


# ---------------------------------------------------------------------------
# Verification / Approval (P6-F06 technician workflow, technical
# verification, authorized approval, finalization)
# ---------------------------------------------------------------------------


async def verify_results(
    db: AsyncSession, current_user: User, lab_order_id: uuid.UUID, *, remarks: str | None = None
) -> VerificationOut:
    """A clean technical review: confirms the entered results and advances
    the order straight through `TECHNICALLY_VERIFIED` into `PENDING_APPROVAL`
    (there is no separate human action between the two - verifying *is*
    queuing for approval). Sibling `reject_verification` is what sends a
    flawed set of results back to `RESULT_ENTERED` for correction."""
    lab_order = await _get_lab_order_or_404(db, lab_order_id)
    ensure_same_tenant(lab_order.tenant_id, current_user)
    ensure_same_facility(lab_order.facility_id, current_user)

    if lab_order.status != "RESULT_ENTERED":
        raise AppError(
            f"Results can only be verified while the order is RESULT_ENTERED (currently {lab_order.status}).",
            code="INVALID_TRANSITION",
        )

    verification = Verification(
        tenant_id=lab_order.tenant_id,
        facility_id=lab_order.facility_id,
        lab_order_id=lab_order.id,
        verified_by=current_user.id,
        status="VERIFIED",
        remarks=remarks,
    )
    db.add(verification)

    results = await db.execute(select(Result).where(Result.lab_order_id == lab_order.id))
    for row in results.scalars().all():
        if row.status == "ENTERED":
            row.status = "VERIFIED"

    await audit_service.record_event(
        db,
        action="lab.results_verified",
        resource_type="lab_order",
        resource_id=lab_order.id,
        after={"remarks": remarks},
        commit=False,
    )
    await db.commit()
    await db.refresh(verification)

    await transition_lab_order_status(db, current_user, lab_order.id, "TECHNICALLY_VERIFIED")
    await transition_lab_order_status(db, current_user, lab_order.id, "PENDING_APPROVAL")

    return VerificationOut.model_validate(verification)


async def reject_verification(
    db: AsyncSession, current_user: User, lab_order_id: uuid.UUID, *, reason: str
) -> VerificationOut:
    lab_order = await _get_lab_order_or_404(db, lab_order_id)
    ensure_same_tenant(lab_order.tenant_id, current_user)
    ensure_same_facility(lab_order.facility_id, current_user)

    if lab_order.status not in ("TECHNICALLY_VERIFIED", "PENDING_APPROVAL"):
        raise AppError(
            f"Verification can only be rejected from TECHNICALLY_VERIFIED/PENDING_APPROVAL "
            f"(currently {lab_order.status}).",
            code="INVALID_TRANSITION",
        )

    verification = Verification(
        tenant_id=lab_order.tenant_id,
        facility_id=lab_order.facility_id,
        lab_order_id=lab_order.id,
        verified_by=current_user.id,
        status="REJECTED",
        remarks=reason,
    )
    db.add(verification)

    results = await db.execute(select(Result).where(Result.lab_order_id == lab_order.id))
    for row in results.scalars().all():
        if row.status == "VERIFIED":
            row.status = "ENTERED"

    await audit_service.record_event(
        db,
        action="lab.results_verification_rejected",
        resource_type="lab_order",
        resource_id=lab_order.id,
        after={"reason": reason},
        commit=False,
    )
    await db.commit()
    await db.refresh(verification)

    await transition_lab_order_status(
        db, current_user, lab_order.id, "RESULT_ENTERED", remarks=reason, required_permission="lab.verify_results"
    )

    return VerificationOut.model_validate(verification)


async def approve_results(
    db: AsyncSession, current_user: User, lab_order_id: uuid.UUID, *, remarks: str | None = None
) -> ApprovalOut:
    lab_order = await _get_lab_order_or_404(db, lab_order_id)
    ensure_same_tenant(lab_order.tenant_id, current_user)
    ensure_same_facility(lab_order.facility_id, current_user)

    if lab_order.status != "PENDING_APPROVAL":
        raise AppError(
            f"Results can only be approved while the order is PENDING_APPROVAL (currently {lab_order.status}).",
            code="INVALID_TRANSITION",
        )

    results = await db.execute(select(Result).where(Result.lab_order_id == lab_order.id))
    result_rows = results.scalars().all()
    for row in result_rows:
        if row.status == "VERIFIED":
            row.status = "APPROVED"

    approval = Approval(
        tenant_id=lab_order.tenant_id,
        facility_id=lab_order.facility_id,
        lab_order_id=lab_order.id,
        approved_by=current_user.id,
        status="APPROVED",
        remarks=remarks,
        report_qr_token=_sign_lab_report(lab_order.id),
        report_checksum=_compute_report_checksum(lab_order.id, result_rows),
    )
    db.add(approval)

    await audit_service.record_event(
        db,
        action="lab.results_approved",
        resource_type="lab_order",
        resource_id=lab_order.id,
        after={"remarks": remarks},
        commit=False,
    )
    await db.commit()
    await db.refresh(approval)

    await transition_lab_order_status(db, current_user, lab_order.id, "APPROVED")

    return ApprovalOut.model_validate(approval)


async def reject_approval(
    db: AsyncSession, current_user: User, lab_order_id: uuid.UUID, *, reason: str
) -> ApprovalOut:
    lab_order = await _get_lab_order_or_404(db, lab_order_id)
    ensure_same_tenant(lab_order.tenant_id, current_user)
    ensure_same_facility(lab_order.facility_id, current_user)

    if lab_order.status != "PENDING_APPROVAL":
        raise AppError(
            f"Approval can only be rejected while the order is PENDING_APPROVAL (currently {lab_order.status}).",
            code="INVALID_TRANSITION",
        )

    approval = Approval(
        tenant_id=lab_order.tenant_id,
        facility_id=lab_order.facility_id,
        lab_order_id=lab_order.id,
        approved_by=current_user.id,
        status="REJECTED",
        remarks=reason,
    )
    db.add(approval)

    results = await db.execute(select(Result).where(Result.lab_order_id == lab_order.id))
    for row in results.scalars().all():
        if row.status == "VERIFIED":
            row.status = "ENTERED"

    await audit_service.record_event(
        db,
        action="lab.results_approval_rejected",
        resource_type="lab_order",
        resource_id=lab_order.id,
        after={"reason": reason},
        commit=False,
    )
    await db.commit()
    await db.refresh(approval)

    await transition_lab_order_status(
        db, current_user, lab_order.id, "RESULT_ENTERED", remarks=reason, required_permission="lab.approve_reports"
    )

    return ApprovalOut.model_validate(approval)


async def finalize_order(db: AsyncSession, current_user: User, lab_order_id: uuid.UUID) -> LabOrderOut:
    return await transition_lab_order_status(db, current_user, lab_order_id, "FINALIZED")


async def list_verifications(
    db: AsyncSession, current_user: User, lab_order_id: uuid.UUID
) -> list[VerificationOut]:
    lab_order = await _get_lab_order_or_404(db, lab_order_id)
    ensure_same_tenant(lab_order.tenant_id, current_user)
    ensure_same_facility(lab_order.facility_id, current_user)

    result = await db.execute(
        select(Verification).where(Verification.lab_order_id == lab_order_id).order_by(Verification.verified_at)
    )
    return [VerificationOut.model_validate(row) for row in result.scalars().all()]


async def list_approvals(
    db: AsyncSession, current_user: User, lab_order_id: uuid.UUID
) -> list[ApprovalOut]:
    lab_order = await _get_lab_order_or_404(db, lab_order_id)
    ensure_same_tenant(lab_order.tenant_id, current_user)
    ensure_same_facility(lab_order.facility_id, current_user)

    result = await db.execute(
        select(Approval).where(Approval.lab_order_id == lab_order_id).order_by(Approval.approved_at)
    )
    return [ApprovalOut.model_validate(row) for row in result.scalars().all()]


# ---------------------------------------------------------------------------
# Report (P6-F07 lab report UI)
# ---------------------------------------------------------------------------

_REPORT_DOC_TYPE = "LAB_REPORT"


def _sign_lab_report(lab_order_id: uuid.UUID) -> str:
    """HMAC-SHA256 over `(doc_type, lab_order_id)`, same technique as
    `opd.qr_security._sign` (same `qr_signing_secret_key`, same truncation)
    but signing a resource identity instead of a bare nonce - this is what
    `docs/document-templates.md` SS3.1's `/verify/doc?t=&id=&sig=` scheme
    needs: a signature a scanner can re-derive from the id/type alone,
    without a prior DB-issued reference."""
    secret = get_settings().qr_signing_secret_key.encode()
    payload = f"{_REPORT_DOC_TYPE}:{lab_order_id}".encode()
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()[:32]


def _compute_report_checksum(lab_order_id: uuid.UUID, result_rows: list[Result]) -> str:
    """A content-integrity marker captured at approval time - not part of
    the QR signature (which only proves "this order id was approved by us",
    not "these exact values"), but useful for detecting whether a result was
    amended after the fact when comparing a stored/printed report against
    the live record."""
    canonical = "|".join(
        f"{row.parameter_id}:{row.value}:{row.flag}"
        for row in sorted(result_rows, key=lambda row: str(row.parameter_id))
    )
    return hashlib.sha256(f"{lab_order_id}:{canonical}".encode()).hexdigest()


async def get_lab_report(db: AsyncSession, current_user: User, lab_order_id: uuid.UUID) -> LabReportOut:
    lab_order = await _get_lab_order_or_404(db, lab_order_id)
    ensure_same_tenant(lab_order.tenant_id, current_user)
    ensure_same_facility(lab_order.facility_id, current_user)

    if lab_order.status not in ("APPROVED", "FINALIZED"):
        raise AppError(
            f"A report is only available once an order is APPROVED or FINALIZED (currently {lab_order.status}).",
            code="INVALID_TRANSITION",
        )

    test = await _get_test_or_404(db, lab_order.test_id)
    patient = await _get_patient_or_404(db, lab_order.patient_id)
    parameters_by_id = {parameter.id: parameter for parameter in test.parameters}

    facility_result = await db.execute(select(Facility).where(Facility.id == lab_order.facility_id))
    facility = facility_result.scalar_one_or_none()

    referring_doctor_name: str | None = None
    if lab_order.ordered_by is not None:
        doctor_result = await db.execute(select(Doctor).where(Doctor.id == lab_order.ordered_by))
        doctor = doctor_result.scalar_one_or_none()
        referring_doctor_name = doctor.full_name if doctor else None

    sample_collected_at: datetime | None = None
    if lab_order.sample_id is not None:
        sample_result = await db.execute(select(Sample).where(Sample.id == lab_order.sample_id))
        sample = sample_result.scalar_one_or_none()
        sample_collected_at = sample.collected_at if sample else None

    accession_number: str | None = None
    if lab_order.accession_id is not None:
        accession_result = await db.execute(select(Accession).where(Accession.id == lab_order.accession_id))
        accession = accession_result.scalar_one_or_none()
        accession_number = accession.accession_number if accession else None

    results = await db.execute(select(Result).where(Result.lab_order_id == lab_order.id))
    rows = [
        ReportResultRow(
            parameter_id=row.parameter_id,
            parameter_code=parameters_by_id[row.parameter_id].parameter_code
            if row.parameter_id in parameters_by_id
            else "",
            parameter_name=parameters_by_id[row.parameter_id].name
            if row.parameter_id in parameters_by_id
            else "",
            value=row.value,
            unit=row.unit,
            flag=row.flag,
            version=row.current_version,
            is_amended=row.status == "AMENDED" or row.current_version > 1,
        )
        for row in results.scalars().all()
    ]

    verification_result = await db.execute(
        select(Verification)
        .where(Verification.lab_order_id == lab_order.id, Verification.status == "VERIFIED")
        .order_by(Verification.verified_at.desc())
    )
    latest_verification = verification_result.scalars().first()
    verified_by_name: str | None = None
    if latest_verification and latest_verification.verified_by:
        verifier_result = await db.execute(select(User).where(User.id == latest_verification.verified_by))
        verifier = verifier_result.scalar_one_or_none()
        verified_by_name = verifier.full_name if verifier else None

    approval_result = await db.execute(
        select(Approval)
        .where(Approval.lab_order_id == lab_order.id, Approval.status == "APPROVED")
        .order_by(Approval.approved_at.desc())
    )
    latest_approval = approval_result.scalars().first()
    approved_by_name: str | None = None
    if latest_approval and latest_approval.approved_by:
        approver_result = await db.execute(select(User).where(User.id == latest_approval.approved_by))
        approver = approver_result.scalar_one_or_none()
        approved_by_name = approver.full_name if approver else None

    today = datetime.now(timezone.utc).date()
    age_years = today.year - patient.dob.year - (
        (today.month, today.day) < (patient.dob.month, patient.dob.day)
    )
    patient_name = " ".join(
        part for part in [patient.title, patient.first_name, patient.middle_name, patient.last_name] if part
    )

    return LabReportOut(
        lab_order_id=lab_order.id,
        order_number=lab_order.order_number,
        accession_number=accession_number,
        status=lab_order.status,
        test_name=test.name,
        priority=lab_order.priority,
        ordered_at=lab_order.ordered_at,
        collected_at=sample_collected_at,
        facility_name=facility.name if facility else "",
        facility_code=facility.facility_code if facility else "",
        patient_name=patient_name,
        patient_uid=patient.uid,
        patient_mrn=patient.mrn,
        patient_gender=patient.gender,
        patient_age_years=age_years,
        referring_doctor_name=referring_doctor_name,
        rows=rows,
        verified_by_name=verified_by_name,
        verified_at=latest_verification.verified_at if latest_verification else None,
        approved_by_name=approved_by_name,
        approved_at=latest_approval.approved_at if latest_approval else None,
        report_checksum=latest_approval.report_checksum if latest_approval else None,
        report_qr_token=latest_approval.report_qr_token if latest_approval else None,
        generated_at=datetime.now(timezone.utc),
    )


async def verify_lab_report(db: AsyncSession, lab_order_id: uuid.UUID, sig: str) -> LabReportVerifyOut:
    """Public, unauthenticated lookup behind the QR's `/verify/doc` link
    (`docs/document-templates.md` SS3.1) - deliberately returns no patient
    data, only enough to confirm the document is genuine and where/when it
    was approved."""
    result = await db.execute(select(LabOrder).where(LabOrder.id == lab_order_id))
    lab_order = result.scalar_one_or_none()
    if lab_order is None or lab_order.status not in ("APPROVED", "FINALIZED"):
        return LabReportVerifyOut(valid=False)

    expected = _sign_lab_report(lab_order_id)
    if not hmac.compare_digest(expected, sig):
        return LabReportVerifyOut(valid=False)

    facility_result = await db.execute(select(Facility).where(Facility.id == lab_order.facility_id))
    facility = facility_result.scalar_one_or_none()

    approval_result = await db.execute(
        select(Approval)
        .where(Approval.lab_order_id == lab_order_id, Approval.status == "APPROVED")
        .order_by(Approval.approved_at.desc())
    )
    latest_approval = approval_result.scalars().first()

    return LabReportVerifyOut(
        valid=True,
        order_number=lab_order.order_number,
        status=lab_order.status,
        facility_name=facility.name if facility else None,
        approved_at=latest_approval.approved_at if latest_approval else None,
    )
