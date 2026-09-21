import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator

PAYMENT_MODES = ("CASH", "CARD", "UPI", "BANK_TRANSFER", "CHEQUE", "INSURANCE")
SERVICE_CATEGORIES = ("CONSULTATION", "PROCEDURE", "DIAGNOSTIC", "ROOM_CHARGE", "PHARMACY", "OTHER")


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ServiceOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    facility_id: uuid.UUID
    department_id: uuid.UUID | None = None
    name: str
    code: str
    category: str
    price: float
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ServiceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=20)
    category: str = Field(default="OTHER")
    price: float = Field(gt=0)
    department_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate_category(self) -> "ServiceCreateRequest":
        if self.category not in SERVICE_CATEGORIES:
            raise ValueError(f"category must be one of {SERVICE_CATEGORIES}")
        return self


class ServiceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = None
    price: float | None = Field(default=None, gt=0)
    department_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None

    @model_validator(mode="after")
    def _validate_category(self) -> "ServiceUpdateRequest":
        if self.category is not None and self.category not in SERVICE_CATEGORIES:
            raise ValueError(f"category must be one of {SERVICE_CATEGORIES}")
        return self


# ---------------------------------------------------------------------------
# Package
# ---------------------------------------------------------------------------


class PackageOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    facility_id: uuid.UUID
    name: str
    code: str
    price: float
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PackageCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=20)
    price: float = Field(gt=0)
    description: str | None = Field(default=None, max_length=500)


class PackageUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    price: float | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------


class InvoiceItemOut(BaseModel):
    id: uuid.UUID
    service_id: uuid.UUID | None = None
    package_id: uuid.UUID | None = None
    item_type: str
    description: str
    quantity: float
    unit_price: float
    discount_amount: float
    tax_amount: float
    total_amount: float

    model_config = {"from_attributes": True}


class InvoiceItemCreateRequest(BaseModel):
    item_type: str
    service_id: uuid.UUID | None = None
    package_id: uuid.UUID | None = None
    description: str | None = Field(default=None, max_length=255)
    quantity: float = Field(default=1.0, gt=0)
    unit_price: float | None = Field(default=None, ge=0)
    discount_amount: float = Field(default=0.0, ge=0)
    tax_amount: float = Field(default=0.0, ge=0)

    @model_validator(mode="after")
    def _validate_item(self) -> "InvoiceItemCreateRequest":
        if self.item_type not in ("SERVICE", "PACKAGE", "CUSTOM"):
            raise ValueError("item_type must be one of SERVICE, PACKAGE, CUSTOM")
        if self.item_type == "SERVICE" and self.service_id is None:
            raise ValueError("service_id is required when item_type is SERVICE")
        if self.item_type == "PACKAGE" and self.package_id is None:
            raise ValueError("package_id is required when item_type is PACKAGE")
        if self.item_type == "CUSTOM" and (self.description is None or self.unit_price is None):
            raise ValueError("description and unit_price are required when item_type is CUSTOM")
        return self


class InvoiceOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    facility_id: uuid.UUID
    patient_id: uuid.UUID
    admission_id: uuid.UUID | None = None
    invoice_number: str
    status: str
    subtotal: float
    discount_amount: float
    tax_amount: float
    total_amount: float
    amount_paid: float
    amount_due: float
    notes: str | None = None
    invoice_date: datetime
    created_at: datetime
    updated_at: datetime
    items: list[InvoiceItemOut] = []

    model_config = {"from_attributes": True}


class InvoiceCreateRequest(BaseModel):
    patient_id: uuid.UUID
    admission_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=1000)
    items: list[InvoiceItemCreateRequest] = Field(min_length=1)


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------


class PaymentOut(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    amount: float
    payment_mode: str
    reference_number: str | None = None
    notes: str | None = None
    status: str
    recorded_at: datetime

    model_config = {"from_attributes": True}


class PaymentCreateRequest(BaseModel):
    amount: float = Field(gt=0)
    payment_mode: str = Field(default="CASH")
    reference_number: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate_mode(self) -> "PaymentCreateRequest":
        if self.payment_mode not in PAYMENT_MODES:
            raise ValueError(f"payment_mode must be one of {PAYMENT_MODES}")
        return self


# ---------------------------------------------------------------------------
# Deposit
# ---------------------------------------------------------------------------


class DepositOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    admission_id: uuid.UUID | None = None
    amount: float
    payment_mode: str
    reference_number: str | None = None
    notes: str | None = None
    status: str
    recorded_at: datetime

    model_config = {"from_attributes": True}


class DepositCreateRequest(BaseModel):
    patient_id: uuid.UUID
    admission_id: uuid.UUID | None = None
    amount: float = Field(gt=0)
    payment_mode: str = Field(default="CASH")
    reference_number: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate_mode(self) -> "DepositCreateRequest":
        if self.payment_mode not in PAYMENT_MODES:
            raise ValueError(f"payment_mode must be one of {PAYMENT_MODES}")
        return self


# ---------------------------------------------------------------------------
# Refund
# ---------------------------------------------------------------------------


class RefundOut(BaseModel):
    id: uuid.UUID
    payment_id: uuid.UUID | None = None
    deposit_id: uuid.UUID | None = None
    amount: float
    reason: str
    refund_mode: str
    notes: str | None = None
    status: str
    recorded_at: datetime

    model_config = {"from_attributes": True}


class RefundCreateRequest(BaseModel):
    payment_id: uuid.UUID | None = None
    deposit_id: uuid.UUID | None = None
    amount: float = Field(gt=0)
    reason: str = Field(min_length=1, max_length=500)
    refund_mode: str = Field(default="CASH")
    notes: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _validate_refund(self) -> "RefundCreateRequest":
        if (self.payment_id is None) == (self.deposit_id is None):
            raise ValueError("Exactly one of payment_id or deposit_id must be provided")
        if self.refund_mode not in PAYMENT_MODES:
            raise ValueError(f"refund_mode must be one of {PAYMENT_MODES}")
        return self


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------


class ReceiptOut(BaseModel):
    id: uuid.UUID
    patient_id: uuid.UUID
    payment_id: uuid.UUID | None = None
    deposit_id: uuid.UUID | None = None
    refund_id: uuid.UUID | None = None
    receipt_number: str
    receipt_type: str
    amount: float
    issued_at: datetime

    model_config = {"from_attributes": True}
