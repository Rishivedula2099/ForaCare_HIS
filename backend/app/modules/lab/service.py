import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import ensure_same_facility, ensure_same_tenant
from app.modules.audit import service as audit_service
from app.modules.auth.models import User
from app.modules.lab.models import Parameter, ReferenceRange, Test
from app.modules.lab.schemas import (
    ParameterCreateRequest,
    ParameterOut,
    ParameterUpdateRequest,
    ReferenceRangeCreateRequest,
    ReferenceRangeOut,
    ReferenceRangeUpdateRequest,
    TestCreateRequest,
    TestOut,
    TestUpdateRequest,
    validate_reference_range_ordering,
)


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
