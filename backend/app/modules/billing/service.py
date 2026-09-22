import hashlib
import json
import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.permissions import ensure_same_facility, ensure_same_tenant
from app.modules.audit import service as audit_service
from app.modules.auth.models import User
from app.modules.billing.models import (
    IdempotencyKey,
    Invoice,
    InvoiceItem,
    Package,
    PatientDeposit,
    Payment,
    Receipt,
    Refund,
    Service,
)
from app.modules.billing.payment_adapter import get_payment_adapter
from app.modules.ipd.models import Admission
from app.modules.billing.schemas import (
    DepositCreateRequest,
    DepositOut,
    InvoiceAddItemsRequest,
    InvoiceBalanceOut,
    InvoiceCreateRequest,
    InvoiceItemCreateRequest,
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
# Decimal-safe money arithmetic (P5-B02)
#
# Invoice/payment/refund fields are `float` end-to-end (schemas.py, models.py)
# to match the rest of the app (see `ipd.models.Deposit.amount`), but a chain
# of float additions/multiplications across several invoice line items can
# drift by a cent or more. `_money` routes every monetary calculation through
# `Decimal` - built from `str(value)` rather than `Decimal(value)` so a float
# like 19.99 doesn't first pick up its imprecise binary representation - and
# rounds to the currency's 2 decimal places before converting back to float
# at the point where a result is assigned to a model/schema field.
# ---------------------------------------------------------------------------

_CENTS = Decimal("0.01")


def _D(value: float | int | Decimal) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _money(*values: float | int | Decimal) -> float:
    """Sums its arguments in `Decimal` and rounds to 2dp. Called with a
    single value to round/convert just that one amount."""
    total = sum((_D(value) for value in values), start=Decimal(0))
    return float(total.quantize(_CENTS, rounding=ROUND_HALF_UP))


def _status_for(amount_paid: Decimal, amount_due: Decimal) -> str:
    if amount_due <= 0:
        return "PAID"
    if amount_paid > 0:
        return "PARTIALLY_PAID"
    return "FINALIZED"


# ---------------------------------------------------------------------------
# Idempotency (P5-B05)
#
# A financial mutation submitted with an `Idempotency-Key` header (wired in
# app/api/v1/billing.py) is keyed by (tenant, scope, key) in
# `billing_idempotency_keys`. `_check_idempotency` must be called - under an
# advisory lock scoped to that same key, so two concurrent retries can't
# both slip past the "not seen yet" check and double-charge - before any
# other work in a mutating function; `_save_idempotency` must be called
# with the final response, in the same transaction as the mutation it
# guards, right before that transaction commits. Only the success path is
# cached, so a request that failed validation can be retried with the same
# key once corrected.
# ---------------------------------------------------------------------------


def _hash_payload(payload: dict) -> str:
    normalized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def _check_idempotency(
    db: AsyncSession, current_user: User, *, scope: str, idempotency_key: str | None, payload: dict
) -> dict | None:
    """Returns the previously cached response for this (scope, key), or
    `None` if this is the first time it's been seen (the caller should
    proceed normally and call `_save_idempotency` when it succeeds)."""
    if idempotency_key is None:
        return None

    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
        {"key": f"billing-idem:{current_user.tenant_id}:{scope}:{idempotency_key}"},
    )

    result = await db.execute(
        select(IdempotencyKey).where(
            IdempotencyKey.tenant_id == current_user.tenant_id,
            IdempotencyKey.scope == scope,
            IdempotencyKey.idempotency_key == idempotency_key,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        return None

    if existing.request_hash != _hash_payload(payload):
        raise ConflictError(
            "This idempotency key was already used for a different request. Use a new key for a new request."
        )
    return existing.response_body


async def _save_idempotency(
    db: AsyncSession,
    current_user: User,
    *,
    scope: str,
    idempotency_key: str | None,
    payload: dict,
    response: dict,
) -> None:
    if idempotency_key is None:
        return
    db.add(
        IdempotencyKey(
            tenant_id=current_user.tenant_id,
            facility_id=current_user.facility_id,
            scope=scope,
            idempotency_key=idempotency_key,
            request_hash=_hash_payload(payload),
            response_body=response,
        )
    )
    await db.flush()


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

    await audit_service.record_event(
        db,
        action="billing.receipt_issued",
        resource_type="billing_receipt",
        resource_id=receipt.id,
        after={"receipt_number": receipt.receipt_number, "receipt_type": receipt_type, "amount": str(amount)},
        commit=False,
    )
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


async def _resolve_line_item(
    db: AsyncSession, current_user: User, item_payload: InvoiceItemCreateRequest
) -> tuple[str, float, Decimal, Decimal, Decimal, Decimal]:
    """Resolves a SERVICE/PACKAGE/CUSTOM line item payload to its
    description, unit price, and Decimal-safe (quantity, discount, tax,
    line_total) figures - shared by `create_invoice` and `add_invoice_items`
    so a line item is priced identically regardless of when it's added."""
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

    quantity = _D(item_payload.quantity)
    discount = _D(item_payload.discount_amount)
    tax = _D(item_payload.tax_amount)
    line_gross = quantity * _D(unit_price)
    line_total = line_gross - discount + tax
    return description, unit_price, line_gross, discount, tax, line_total


async def _append_invoice_items(
    db: AsyncSession,
    invoice: Invoice,
    items: list[InvoiceItemCreateRequest],
    current_user: User,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Prices and inserts `InvoiceItem` rows for `items` against `invoice`,
    returning the (gross, discount, tax, line_total) sums to fold into the
    invoice's running totals - shared by `create_invoice` (starting from
    zero) and `add_invoice_items` (added to the existing totals)."""
    added_gross = Decimal(0)
    added_discount = Decimal(0)
    added_tax = Decimal(0)
    added_total = Decimal(0)

    for item_payload in items:
        description, unit_price, line_gross, discount, tax, line_total = await _resolve_line_item(
            db, current_user, item_payload
        )
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
                total_amount=_money(line_total),
            )
        )
        added_gross += line_gross
        added_discount += discount
        added_tax += tax
        added_total += line_total

    return added_gross, added_discount, added_tax, added_total


async def create_invoice(
    db: AsyncSession,
    payload: InvoiceCreateRequest,
    current_user: User,
    *,
    idempotency_key: str | None = None,
) -> InvoiceOut:
    request_payload = payload.model_dump(mode="json")
    cached = await _check_idempotency(
        db, current_user, scope="create_invoice", idempotency_key=idempotency_key, payload=request_payload
    )
    if cached is not None:
        return InvoiceOut.model_validate(cached)

    patient = await _get_patient_or_404(db, payload.patient_id)
    ensure_same_tenant(patient.tenant_id, current_user)
    ensure_same_facility(patient.facility_id, current_user)

    if payload.admission_id is not None:
        admission = await db.get(Admission, payload.admission_id)
        if admission is None:
            raise NotFoundError("Admission not found.")
        ensure_same_tenant(admission.tenant_id, current_user)
        ensure_same_facility(admission.facility_id, current_user)

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

    subtotal, discount_total, tax_total, grand_total = await _append_invoice_items(
        db, invoice, payload.items, current_user
    )

    invoice.subtotal = _money(subtotal)
    invoice.discount_amount = _money(discount_total)
    invoice.tax_amount = _money(tax_total)
    invoice.total_amount = _money(grand_total)
    invoice.amount_paid = 0.0
    invoice.amount_due = _money(grand_total)
    await db.flush()

    await audit_service.record_event(
        db,
        action="billing.invoice_created",
        resource_type="billing_invoice",
        resource_id=invoice.id,
        after={"invoice_number": invoice.invoice_number, "total_amount": str(grand_total)},
        commit=False,
    )
    result = await get_invoice(db, invoice.id, current_user)
    await _save_idempotency(
        db,
        current_user,
        scope="create_invoice",
        idempotency_key=idempotency_key,
        payload=request_payload,
        response=result.model_dump(mode="json"),
    )
    await db.commit()
    return result


async def add_invoice_items(
    db: AsyncSession,
    invoice_id: uuid.UUID,
    payload: InvoiceAddItemsRequest,
    current_user: User,
    *,
    idempotency_key: str | None = None,
) -> InvoiceOut:
    request_payload = {"invoice_id": str(invoice_id), **payload.model_dump(mode="json")}
    cached = await _check_idempotency(
        db, current_user, scope="add_invoice_items", idempotency_key=idempotency_key, payload=request_payload
    )
    if cached is not None:
        return InvoiceOut.model_validate(cached)

    invoice = await _get_invoice_or_404(db, invoice_id, for_update=True)
    ensure_same_tenant(invoice.tenant_id, current_user)
    ensure_same_facility(invoice.facility_id, current_user)

    if invoice.status == "CANCELLED":
        raise ConflictError("Cannot add items to a cancelled invoice.")
    if invoice.status == "PAID":
        raise ConflictError("Cannot add items to a fully paid invoice.")

    added_gross, added_discount, added_tax, added_total = await _append_invoice_items(
        db, invoice, payload.items, current_user
    )

    new_amount_due = _D(invoice.amount_due) + added_total
    invoice.subtotal = _money(_D(invoice.subtotal) + added_gross)
    invoice.discount_amount = _money(_D(invoice.discount_amount) + added_discount)
    invoice.tax_amount = _money(_D(invoice.tax_amount) + added_tax)
    invoice.total_amount = _money(_D(invoice.total_amount) + added_total)
    invoice.amount_due = _money(new_amount_due)
    invoice.status = _status_for(_D(invoice.amount_paid), new_amount_due)
    await db.flush()

    await audit_service.record_event(
        db,
        action="billing.invoice_items_added",
        resource_type="billing_invoice",
        resource_id=invoice.id,
        after={"added_total": str(added_total), "new_total_amount": invoice.total_amount},
        commit=False,
    )
    result = await get_invoice(db, invoice.id, current_user)
    await _save_idempotency(
        db,
        current_user,
        scope="add_invoice_items",
        idempotency_key=idempotency_key,
        payload=request_payload,
        response=result.model_dump(mode="json"),
    )
    await db.commit()
    return result


async def get_invoice_balance(
    db: AsyncSession, invoice_id: uuid.UUID, current_user: User
) -> InvoiceBalanceOut:
    invoice = await _get_invoice_or_404(db, invoice_id)
    ensure_same_tenant(invoice.tenant_id, current_user)
    ensure_same_facility(invoice.facility_id, current_user)
    return InvoiceBalanceOut(
        invoice_id=invoice.id,
        invoice_number=invoice.invoice_number,
        status=invoice.status,
        total_amount=invoice.total_amount,
        amount_paid=invoice.amount_paid,
        amount_due=invoice.amount_due,
    )


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------


async def record_payment(
    db: AsyncSession,
    invoice_id: uuid.UUID,
    payload: PaymentCreateRequest,
    current_user: User,
    *,
    idempotency_key: str | None = None,
) -> PaymentOut:
    request_payload = {"invoice_id": str(invoice_id), **payload.model_dump(mode="json")}
    cached = await _check_idempotency(
        db, current_user, scope="record_payment", idempotency_key=idempotency_key, payload=request_payload
    )
    if cached is not None:
        return PaymentOut.model_validate(cached)

    invoice = await _get_invoice_or_404(db, invoice_id, for_update=True)
    ensure_same_tenant(invoice.tenant_id, current_user)
    ensure_same_facility(invoice.facility_id, current_user)

    if invoice.status == "CANCELLED":
        raise ConflictError("Cannot record a payment against a cancelled invoice.")

    amount = _D(payload.amount)
    amount_due = _D(invoice.amount_due)
    if amount > amount_due:
        raise ConflictError("Payment amount exceeds the outstanding balance on this invoice.")

    adapter = get_payment_adapter()
    adapter_result = await adapter.process_payment(
        amount=payload.amount, payment_mode=payload.payment_mode, reference_number=payload.reference_number
    )
    if not adapter_result.success:
        raise ConflictError(adapter_result.message or "Payment could not be processed.")

    payment = Payment(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        invoice_id=invoice.id,
        received_by=current_user.id,
        amount=payload.amount,
        payment_mode=payload.payment_mode,
        reference_number=adapter_result.transaction_reference,
        notes=payload.notes,
    )
    db.add(payment)

    new_amount_paid = _D(invoice.amount_paid) + amount
    new_amount_due = amount_due - amount
    invoice.amount_paid = _money(new_amount_paid)
    invoice.amount_due = _money(new_amount_due)
    invoice.status = _status_for(new_amount_paid, new_amount_due)
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
    payment_out = PaymentOut.model_validate(payment)
    await _save_idempotency(
        db,
        current_user,
        scope="record_payment",
        idempotency_key=idempotency_key,
        payload=request_payload,
        response=payment_out.model_dump(mode="json"),
    )
    await db.commit()
    return payment_out


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
    db: AsyncSession,
    payload: DepositCreateRequest,
    current_user: User,
    *,
    idempotency_key: str | None = None,
) -> DepositOut:
    request_payload = payload.model_dump(mode="json")
    cached = await _check_idempotency(
        db, current_user, scope="record_deposit", idempotency_key=idempotency_key, payload=request_payload
    )
    if cached is not None:
        return DepositOut.model_validate(cached)

    patient = await _get_patient_or_404(db, payload.patient_id)
    ensure_same_tenant(patient.tenant_id, current_user)
    ensure_same_facility(patient.facility_id, current_user)

    adapter = get_payment_adapter()
    adapter_result = await adapter.process_payment(
        amount=payload.amount, payment_mode=payload.payment_mode, reference_number=payload.reference_number
    )
    if not adapter_result.success:
        raise ConflictError(adapter_result.message or "Deposit could not be processed.")

    deposit = PatientDeposit(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        patient_id=payload.patient_id,
        admission_id=payload.admission_id,
        received_by=current_user.id,
        amount=payload.amount,
        payment_mode=payload.payment_mode,
        reference_number=adapter_result.transaction_reference,
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
    deposit_out = DepositOut.model_validate(deposit)
    await _save_idempotency(
        db,
        current_user,
        scope="record_deposit",
        idempotency_key=idempotency_key,
        payload=request_payload,
        response=deposit_out.model_dump(mode="json"),
    )
    await db.commit()
    return deposit_out


# ---------------------------------------------------------------------------
# Refund
# ---------------------------------------------------------------------------


async def create_refund(
    db: AsyncSession,
    payload: RefundCreateRequest,
    current_user: User,
    *,
    idempotency_key: str | None = None,
) -> RefundOut:
    request_payload = payload.model_dump(mode="json")
    cached = await _check_idempotency(
        db, current_user, scope="create_refund", idempotency_key=idempotency_key, payload=request_payload
    )
    if cached is not None:
        return RefundOut.model_validate(cached)

    patient_id: uuid.UUID
    original_reference: str | None

    if payload.payment_id is not None:
        payment = await db.get(Payment, payload.payment_id)
        if payment is None:
            raise NotFoundError("Payment not found.")
        ensure_same_tenant(payment.tenant_id, current_user)
        ensure_same_facility(payment.facility_id, current_user)
        if payment.status == "REFUNDED":
            raise ConflictError("This payment has already been refunded.")
        refund_amount = _D(payload.amount)
        if refund_amount > _D(payment.amount):
            raise ConflictError("Refund amount exceeds the original payment amount.")
        original_reference = payment.reference_number

        invoice = await _get_invoice_or_404(db, payment.invoice_id, for_update=True)
        new_amount_paid = _D(invoice.amount_paid) - refund_amount
        new_amount_due = _D(invoice.amount_due) + refund_amount
        invoice.amount_paid = _money(new_amount_paid)
        invoice.amount_due = _money(new_amount_due)
        invoice.status = _status_for(new_amount_paid, new_amount_due)
        payment.status = "REFUNDED"
        patient_id = invoice.patient_id
    else:
        deposit = await _get_deposit_or_404(db, payload.deposit_id, for_update=True)
        ensure_same_tenant(deposit.tenant_id, current_user)
        ensure_same_facility(deposit.facility_id, current_user)
        if deposit.status == "REFUNDED":
            raise ConflictError("This deposit has already been refunded.")
        if _D(payload.amount) > _D(deposit.amount):
            raise ConflictError("Refund amount exceeds the original deposit amount.")
        original_reference = deposit.reference_number
        deposit.status = "REFUNDED"
        patient_id = deposit.patient_id

    adapter = get_payment_adapter()
    adapter_result = await adapter.process_refund(
        amount=payload.amount, refund_mode=payload.refund_mode, original_reference=original_reference
    )
    if not adapter_result.success:
        raise ConflictError(adapter_result.message or "Refund could not be processed.")

    refund = Refund(
        tenant_id=current_user.tenant_id,
        facility_id=current_user.facility_id,
        payment_id=payload.payment_id,
        deposit_id=payload.deposit_id,
        processed_by=current_user.id,
        amount=payload.amount,
        reason=payload.reason,
        refund_mode=payload.refund_mode,
        gateway_reference=adapter_result.transaction_reference,
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
    refund_out = RefundOut.model_validate(refund)
    await _save_idempotency(
        db,
        current_user,
        scope="create_refund",
        idempotency_key=idempotency_key,
        payload=request_payload,
        response=refund_out.model_dump(mode="json"),
    )
    await db.commit()
    return refund_out


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


async def list_receipts(
    db: AsyncSession,
    current_user: User,
    *,
    patient_id: uuid.UUID | None = None,
    payment_id: uuid.UUID | None = None,
    deposit_id: uuid.UUID | None = None,
    refund_id: uuid.UUID | None = None,
) -> list[ReceiptOut]:
    """Looks up the receipt(s) issued for a payment/deposit/refund - each of
    those endpoints returns only its own record, not the `Receipt` row
    `_issue_receipt` creates alongside it, so a caller (the cashier UI,
    wanting to preview/print the receipt right after collecting a payment)
    needs this to find it."""
    stmt = select(Receipt).where(
        Receipt.tenant_id == current_user.tenant_id, Receipt.facility_id == current_user.facility_id
    )
    if patient_id is not None:
        stmt = stmt.where(Receipt.patient_id == patient_id)
    if payment_id is not None:
        stmt = stmt.where(Receipt.payment_id == payment_id)
    if deposit_id is not None:
        stmt = stmt.where(Receipt.deposit_id == deposit_id)
    if refund_id is not None:
        stmt = stmt.where(Receipt.refund_id == refund_id)
    stmt = stmt.order_by(Receipt.issued_at.desc())

    result = await db.execute(stmt)
    return [ReceiptOut.model_validate(receipt) for receipt in result.scalars().all()]
