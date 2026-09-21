import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import ensure_same_facility, ensure_same_tenant
from app.modules.audit import service as audit_service
from app.modules.auth.models import User
from app.modules.billing.models import (
    Invoice,
    InvoiceItem,
    Package,
    PatientDeposit,
    Payment,
    Receipt,
    Refund,
    Service,
)
from app.modules.billing.schemas import (
    DepositCreateRequest,
    DepositOut,
    InvoiceCreateRequest,
    InvoiceOut,
    PackageCreateRequest,
    PackageOut,
    PackageUpdateRequest,
    PaymentCreateRequest,
    PaymentOut,
    ReceiptOut,
    RefundCreateRequest,
    RefundOut,
    ServiceCreateRequest,
    ServiceOut,
    ServiceUpdateRequest,
)
from app.modules.patients.models import Patient


async def _get_patient_or_404(db: AsyncSession, patient_id: uuid.UUID) -> Patient:
    result = await db.execute(select(Patient).where(Patient.id == patient_id))
    patient = result.scalar_one_or_none()
    if patient is None:
        raise NotFoundError("Patient not found.")
    return patient


# ---------------------------------------------------------------------------
# Number sequences
#
# Mirrors `_lock_admission_number_sequence`/`_generate_admission_number` in
# app/modules/ipd/service.py: an advisory lock serializes generation for one
# tenant+sequence so two concurrent requests can't compute the same number
# before either row exists to `SELECT ... FOR UPDATE`.
# ---------------------------------------------------------------------------


async def _lock_number_sequence(db: AsyncSession, tenant_id: uuid.UUID, sequence: str) -> None:
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
        {"key": f"billing-{sequence}-number:{tenant_id}"},
    )


async def _generate_invoice_number(db: AsyncSession, current_user: User) -> str:
    await _lock_number_sequence(db, current_user.tenant_id, "invoice")
    year = datetime.now(timezone.utc).strftime("%Y")
    result = await db.execute(
        select(func.count()).select_from(Invoice).where(Invoice.tenant_id == current_user.tenant_id)
    )
    count = result.scalar_one()
    return f"INV-{year}-{count + 1:06d}"


async def _generate_receipt_number(db: AsyncSession, current_user: User) -> str:
    await _lock_number_sequence(db, current_user.tenant_id, "receipt")
    year = datetime.now(timezone.utc).strftime("%Y")
    result = await db.execute(
        select(func.count()).select_from(Receipt).where(Receipt.tenant_id == current_user.tenant_id)
    )
    count = result.scalar_one()
    return f"RCPT-{year}-{count + 1:06d}"


async def _issue_receipt(
    db: AsyncSession,
    current_user: User,
    *,
    patient_id: uuid.UUID,
    receipt_type: str,
    amount: float,
    payment_id: uuid.UUID | None = None,
    deposit_id: uuid.UUID | None = None,
    refund_id: uuid.UUID | None = None,
) -> Receipt:
    receipt = Receipt(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        patient_id=patient_id,
        payment_id=payment_id,
        deposit_id=deposit_id,
        refund_id=refund_id,
        issued_by=current_user.id,
        receipt_number=await _generate_receipt_number(db, current_user),
        receipt_type=receipt_type,
        amount=amount,
    )
    db.add(receipt)
    await db.flush()
    return receipt


# ---------------------------------------------------------------------------
# Service (master)
# ---------------------------------------------------------------------------


async def list_services(
    db: AsyncSession, current_user: User, *, name: str | None = None, is_active: bool | None = None
) -> list[ServiceOut]:
    stmt = select(Service).where(
        Service.tenant_id == current_user.tenant_id, Service.facility_id == current_user.facility_id
    )
    if name:
        stmt = stmt.where(Service.name.ilike(f"%{name}%"))
    if is_active is not None:
        stmt = stmt.where(Service.is_active == is_active)
    stmt = stmt.order_by(Service.name)

    result = await db.execute(stmt)
    return [ServiceOut.model_validate(service) for service in result.scalars().all()]


async def _get_service_or_404(db: AsyncSession, service_id: uuid.UUID) -> Service:
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    if service is None:
        raise NotFoundError("Service not found.")
    return service


async def get_service(db: AsyncSession, service_id: uuid.UUID, current_user: User) -> ServiceOut:
    service = await _get_service_or_404(db, service_id)
    ensure_same_tenant(service.tenant_id, current_user)
    ensure_same_facility(service.facility_id, current_user)
    return ServiceOut.model_validate(service)


async def create_service(
    db: AsyncSession, payload: ServiceCreateRequest, current_user: User
) -> ServiceOut:
    existing = await db.execute(
        select(Service).where(
            Service.facility_id == current_user.facility_id, Service.code == payload.code
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A service with this code already exists in this facility.")

    service = Service(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        **payload.model_dump(),
    )
    db.add(service)
    await db.flush()

    await audit_service.record_event(
        db,
        action="billing.service_created",
        resource_type="billing_service",
        resource_id=service.id,
        after=ServiceOut.model_validate(service).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(service)
    return ServiceOut.model_validate(service)


async def update_service(
    db: AsyncSession, service_id: uuid.UUID, payload: ServiceUpdateRequest, current_user: User
) -> ServiceOut:
    service = await _get_service_or_404(db, service_id)
    ensure_same_tenant(service.tenant_id, current_user)
    ensure_same_facility(service.facility_id, current_user)

    before = ServiceOut.model_validate(service).model_dump(mode="json")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(service, field, value)
    await db.flush()

    await audit_service.record_event(
        db,
        action="billing.service_updated",
        resource_type="billing_service",
        resource_id=service.id,
        before=before,
        after=ServiceOut.model_validate(service).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(service)
    return ServiceOut.model_validate(service)


# ---------------------------------------------------------------------------
# Package (master)
# ---------------------------------------------------------------------------


async def list_packages(
    db: AsyncSession, current_user: User, *, name: str | None = None, is_active: bool | None = None
) -> list[PackageOut]:
    stmt = select(Package).where(
        Package.tenant_id == current_user.tenant_id, Package.facility_id == current_user.facility_id
    )
    if name:
        stmt = stmt.where(Package.name.ilike(f"%{name}%"))
    if is_active is not None:
        stmt = stmt.where(Package.is_active == is_active)
    stmt = stmt.order_by(Package.name)

    result = await db.execute(stmt)
    return [PackageOut.model_validate(package) for package in result.scalars().all()]


async def _get_package_or_404(db: AsyncSession, package_id: uuid.UUID) -> Package:
    result = await db.execute(select(Package).where(Package.id == package_id))
    package = result.scalar_one_or_none()
    if package is None:
        raise NotFoundError("Package not found.")
    return package


async def get_package(db: AsyncSession, package_id: uuid.UUID, current_user: User) -> PackageOut:
    package = await _get_package_or_404(db, package_id)
    ensure_same_tenant(package.tenant_id, current_user)
    ensure_same_facility(package.facility_id, current_user)
    return PackageOut.model_validate(package)


async def create_package(
    db: AsyncSession, payload: PackageCreateRequest, current_user: User
) -> PackageOut:
    existing = await db.execute(
        select(Package).where(
            Package.facility_id == current_user.facility_id, Package.code == payload.code
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("A package with this code already exists in this facility.")

    package = Package(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        **payload.model_dump(),
    )
    db.add(package)
    await db.flush()

    await audit_service.record_event(
        db,
        action="billing.package_created",
        resource_type="billing_package",
        resource_id=package.id,
        after=PackageOut.model_validate(package).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(package)
    return PackageOut.model_validate(package)


async def update_package(
    db: AsyncSession, package_id: uuid.UUID, payload: PackageUpdateRequest, current_user: User
) -> PackageOut:
    package = await _get_package_or_404(db, package_id)
    ensure_same_tenant(package.tenant_id, current_user)
    ensure_same_facility(package.facility_id, current_user)

    before = PackageOut.model_validate(package).model_dump(mode="json")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(package, field, value)
    await db.flush()

    await audit_service.record_event(
        db,
        action="billing.package_updated",
        resource_type="billing_package",
        resource_id=package.id,
        before=before,
        after=PackageOut.model_validate(package).model_dump(mode="json"),
        commit=False,
    )
    await db.commit()
    await db.refresh(package)
    return PackageOut.model_validate(package)


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------


async def list_invoices(
    db: AsyncSession,
    current_user: User,
    *,
    patient_id: uuid.UUID | None = None,
    status: str | None = None,
) -> list[InvoiceOut]:
    stmt = select(Invoice).where(
        Invoice.tenant_id == current_user.tenant_id, Invoice.facility_id == current_user.facility_id
    )
    if patient_id:
        stmt = stmt.where(Invoice.patient_id == patient_id)
    if status:
        stmt = stmt.where(Invoice.status == status)
    stmt = stmt.order_by(Invoice.invoice_date.desc())

    result = await db.execute(stmt)
    return [InvoiceOut.model_validate(invoice) for invoice in result.scalars().all()]


async def _get_invoice_or_404(
    db: AsyncSession, invoice_id: uuid.UUID, *, for_update: bool = False
) -> Invoice:
    stmt = select(Invoice).where(Invoice.id == invoice_id)
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    invoice = result.scalar_one_or_none()
    if invoice is None:
        raise NotFoundError("Invoice not found.")
    return invoice


async def get_invoice(db: AsyncSession, invoice_id: uuid.UUID, current_user: User) -> InvoiceOut:
    invoice = await _get_invoice_or_404(db, invoice_id)
    ensure_same_tenant(invoice.tenant_id, current_user)
    ensure_same_facility(invoice.facility_id, current_user)
    return InvoiceOut.model_validate(invoice)


async def create_invoice(
    db: AsyncSession, payload: InvoiceCreateRequest, current_user: User
) -> InvoiceOut:
    patient = await _get_patient_or_404(db, payload.patient_id)
    ensure_same_tenant(patient.tenant_id, current_user)
    ensure_same_facility(patient.facility_id, current_user)

    invoice = Invoice(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        patient_id=payload.patient_id,
        admission_id=payload.admission_id,
        created_by=current_user.id,
        notes=payload.notes,
        invoice_number=await _generate_invoice_number(db, current_user),
    )
    db.add(invoice)
    await db.flush()

    subtotal = 0.0
    discount_total = 0.0
    tax_total = 0.0
    grand_total = 0.0

    for item_payload in payload.items:
        unit_price = item_payload.unit_price
        description = item_payload.description
        if item_payload.item_type == "SERVICE":
            service = await _get_service_or_404(db, item_payload.service_id)
            ensure_same_tenant(service.tenant_id, current_user)
            ensure_same_facility(service.facility_id, current_user)
            unit_price = unit_price if unit_price is not None else float(service.price)
            description = description or service.name
        elif item_payload.item_type == "PACKAGE":
            package = await _get_package_or_404(db, item_payload.package_id)
            ensure_same_tenant(package.tenant_id, current_user)
            ensure_same_facility(package.facility_id, current_user)
            unit_price = unit_price if unit_price is not None else float(package.price)
            description = description or package.name

        line_gross = item_payload.quantity * unit_price
        line_total = line_gross - item_payload.discount_amount + item_payload.tax_amount

        db.add(
            InvoiceItem(
                tenant_id=current_user.tenant_id,
                facility_id=current_user.facility_id,
                invoice_id=invoice.id,
                service_id=item_payload.service_id,
                package_id=item_payload.package_id,
                item_type=item_payload.item_type,
                description=description,
                quantity=item_payload.quantity,
                unit_price=unit_price,
                discount_amount=item_payload.discount_amount,
                tax_amount=item_payload.tax_amount,
                total_amount=line_total,
            )
        )

        subtotal += line_gross
        discount_total += item_payload.discount_amount
        tax_total += item_payload.tax_amount
        grand_total += line_total

    invoice.subtotal = subtotal
    invoice.discount_amount = discount_total
    invoice.tax_amount = tax_total
    invoice.total_amount = grand_total
    invoice.amount_paid = 0.0
    invoice.amount_due = grand_total
    await db.flush()

    await audit_service.record_event(
        db,
        action="billing.invoice_created",
        resource_type="billing_invoice",
        resource_id=invoice.id,
        after={"invoice_number": invoice.invoice_number, "total_amount": str(grand_total)},
        commit=False,
    )
    await db.commit()
    await db.refresh(invoice)
    return await get_invoice(db, invoice.id, current_user)


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------


async def record_payment(
    db: AsyncSession, invoice_id: uuid.UUID, payload: PaymentCreateRequest, current_user: User
) -> PaymentOut:
    invoice = await _get_invoice_or_404(db, invoice_id, for_update=True)
    ensure_same_tenant(invoice.tenant_id, current_user)
    ensure_same_facility(invoice.facility_id, current_user)

    if invoice.status == "CANCELLED":
        raise ConflictError("Cannot record a payment against a cancelled invoice.")
    if payload.amount > invoice.amount_due:
        raise ConflictError("Payment amount exceeds the outstanding balance on this invoice.")

    payment = Payment(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        invoice_id=invoice.id,
        received_by=current_user.id,
        amount=payload.amount,
        payment_mode=payload.payment_mode,
        reference_number=payload.reference_number,
        notes=payload.notes,
    )
    db.add(payment)

    invoice.amount_paid = float(invoice.amount_paid) + payload.amount
    invoice.amount_due = float(invoice.amount_due) - payload.amount
    invoice.status = "PAID" if invoice.amount_due <= 0 else "PARTIALLY_PAID"
    await db.flush()

    await _issue_receipt(
        db,
        current_user,
        patient_id=invoice.patient_id,
        receipt_type="PAYMENT",
        amount=payload.amount,
        payment_id=payment.id,
    )

    await audit_service.record_event(
        db,
        action="billing.payment_recorded",
        resource_type="billing_payment",
        resource_id=payment.id,
        after={"invoice_id": str(invoice.id), "amount": str(payload.amount)},
        commit=False,
    )
    await db.commit()
    await db.refresh(payment)
    return PaymentOut.model_validate(payment)


async def list_payments(db: AsyncSession, invoice_id: uuid.UUID, current_user: User) -> list[PaymentOut]:
    invoice = await _get_invoice_or_404(db, invoice_id)
    ensure_same_tenant(invoice.tenant_id, current_user)
    ensure_same_facility(invoice.facility_id, current_user)
    return [PaymentOut.model_validate(payment) for payment in invoice.payments]


# ---------------------------------------------------------------------------
# PatientDeposit
# ---------------------------------------------------------------------------


async def list_deposits(db: AsyncSession, current_user: User, *, patient_id: uuid.UUID | None = None) -> list[DepositOut]:
    stmt = select(PatientDeposit).where(
        PatientDeposit.tenant_id == current_user.tenant_id, PatientDeposit.facility_id == current_user.facility_id
    )
    if patient_id:
        stmt = stmt.where(PatientDeposit.patient_id == patient_id)
    stmt = stmt.order_by(PatientDeposit.recorded_at.desc())

    result = await db.execute(stmt)
    return [DepositOut.model_validate(deposit) for deposit in result.scalars().all()]


async def _get_deposit_or_404(
    db: AsyncSession, deposit_id: uuid.UUID, *, for_update: bool = False
) -> PatientDeposit:
    stmt = select(PatientDeposit).where(PatientDeposit.id == deposit_id)
    if for_update:
        stmt = stmt.with_for_update()
    result = await db.execute(stmt)
    deposit = result.scalar_one_or_none()
    if deposit is None:
        raise NotFoundError("Deposit not found.")
    return deposit


async def record_deposit(
    db: AsyncSession, payload: DepositCreateRequest, current_user: User
) -> DepositOut:
    patient = await _get_patient_or_404(db, payload.patient_id)
    ensure_same_tenant(patient.tenant_id, current_user)
    ensure_same_facility(patient.facility_id, current_user)

    deposit = PatientDeposit(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        patient_id=payload.patient_id,
        admission_id=payload.admission_id,
        received_by=current_user.id,
        amount=payload.amount,
        payment_mode=payload.payment_mode,
        reference_number=payload.reference_number,
        notes=payload.notes,
    )
    db.add(deposit)
    await db.flush()

    await _issue_receipt(
        db,
        current_user,
        patient_id=deposit.patient_id,
        receipt_type="DEPOSIT",
        amount=deposit.amount,
        deposit_id=deposit.id,
    )

    await audit_service.record_event(
        db,
        action="billing.deposit_recorded",
        resource_type="billing_deposit",
        resource_id=deposit.id,
        after={"patient_id": str(deposit.patient_id), "amount": str(payload.amount)},
        commit=False,
    )
    await db.commit()
    await db.refresh(deposit)
    return DepositOut.model_validate(deposit)


# ---------------------------------------------------------------------------
# Refund
# ---------------------------------------------------------------------------


async def create_refund(
    db: AsyncSession, payload: RefundCreateRequest, current_user: User
) -> RefundOut:
    patient_id: uuid.UUID

    if payload.payment_id is not None:
        payment = await db.get(Payment, payload.payment_id)
        if payment is None:
            raise NotFoundError("Payment not found.")
        ensure_same_tenant(payment.tenant_id, current_user)
        ensure_same_facility(payment.facility_id, current_user)
        if payment.status == "REFUNDED":
            raise ConflictError("This payment has already been refunded.")
        if payload.amount > payment.amount:
            raise ConflictError("Refund amount exceeds the original payment amount.")

        invoice = await _get_invoice_or_404(db, payment.invoice_id, for_update=True)
        invoice.amount_paid = float(invoice.amount_paid) - payload.amount
        invoice.amount_due = float(invoice.amount_due) + payload.amount
        invoice.status = "PARTIALLY_PAID" if invoice.amount_paid > 0 else "FINALIZED"
        payment.status = "REFUNDED"
        patient_id = invoice.patient_id
    else:
        deposit = await _get_deposit_or_404(db, payload.deposit_id, for_update=True)
        ensure_same_tenant(deposit.tenant_id, current_user)
        ensure_same_facility(deposit.facility_id, current_user)
        if deposit.status == "REFUNDED":
            raise ConflictError("This deposit has already been refunded.")
        if payload.amount > deposit.amount:
            raise ConflictError("Refund amount exceeds the original deposit amount.")
        deposit.status = "REFUNDED"
        patient_id = deposit.patient_id

    refund = Refund(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        payment_id=payload.payment_id,
        deposit_id=payload.deposit_id,
        processed_by=current_user.id,
        amount=payload.amount,
        reason=payload.reason,
        refund_mode=payload.refund_mode,
        notes=payload.notes,
    )
    db.add(refund)
    await db.flush()

    await _issue_receipt(
        db,
        current_user,
        patient_id=patient_id,
        receipt_type="REFUND",
        amount=payload.amount,
        refund_id=refund.id,
    )

    await audit_service.record_event(
        db,
        action="billing.refund_created",
        resource_type="billing_refund",
        resource_id=refund.id,
        after={"amount": str(payload.amount), "reason": payload.reason},
        commit=False,
    )
    await db.commit()
    await db.refresh(refund)
    return RefundOut.model_validate(refund)


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------


async def get_receipt(db: AsyncSession, receipt_id: uuid.UUID, current_user: User) -> ReceiptOut:
    receipt = await db.get(Receipt, receipt_id)
    if receipt is None:
        raise NotFoundError("Receipt not found.")
    ensure_same_tenant(receipt.tenant_id, current_user)
    ensure_same_facility(receipt.facility_id, current_user)
    return ReceiptOut.model_validate(receipt)
