"""Payment settlement abstraction (P5-B04).

`PaymentAdapter` is the seam between the payment-recording logic in
app/modules/billing/service.py and however a payment is actually settled.
ForaCare HIS is a cashier-counter billing system - CASH/CARD/UPI are
collected and confirmed by the cashier in person, and CORPORATE/INSURANCE/
FREE/OTHER never touch a live gateway at all - so `MockPaymentAdapter` (the
only implementation today) settles every payment and refund immediately and
locally rather than calling out to anything.

A future production adapter (e.g. a real card/UPI payment gateway
integration, should one ever be needed) implements the same interface and
is selected via `get_payment_adapter()`, so `service.py`'s calls to
`process_payment`/`process_refund` never change.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class PaymentAdapterResult:
    success: bool
    transaction_reference: str | None = None
    message: str | None = None


class PaymentAdapter(ABC):
    """Settles one payment or refund for a mode in `billing.schemas.PAYMENT_MODES`."""

    @abstractmethod
    async def process_payment(
        self, *, amount: float, payment_mode: str, reference_number: str | None
    ) -> PaymentAdapterResult:
        """Settles a payment. `reference_number` is whatever the cashier
        already entered (a UPI transaction ID, a cheque number) - the
        adapter may pass it through, validate it, or fill one in when it's
        blank, but never overwrites one the cashier gave."""

    @abstractmethod
    async def process_refund(
        self, *, amount: float, refund_mode: str, original_reference: str | None
    ) -> PaymentAdapterResult:
        """Settles a refund against `original_reference` (the payment's or
        deposit's own reference/id, for a gateway that needs it to reverse
        the original transaction)."""


class MockPaymentAdapter(PaymentAdapter):
    """Settles every payment/refund immediately and successfully, generating
    a synthetic reference when the caller didn't supply one. This is the
    only adapter in use until a real gateway integration is needed - fine
    for a cashier-counter system where the money has already changed hands
    by the time this runs, and a stand-in for tests."""

    async def process_payment(
        self, *, amount: float, payment_mode: str, reference_number: str | None
    ) -> PaymentAdapterResult:
        del amount, payment_mode  # unused by the mock; part of the interface
        reference = reference_number or f"MOCK-{uuid.uuid4().hex[:12].upper()}"
        return PaymentAdapterResult(success=True, transaction_reference=reference)

    async def process_refund(
        self, *, amount: float, refund_mode: str, original_reference: str | None
    ) -> PaymentAdapterResult:
        del amount, refund_mode, original_reference  # unused by the mock
        reference = f"MOCK-RFND-{uuid.uuid4().hex[:12].upper()}"
        return PaymentAdapterResult(success=True, transaction_reference=reference)


def get_payment_adapter() -> PaymentAdapter:
    """Selects the `PaymentAdapter` implementation named by
    `Settings.payment_adapter`. A future production adapter adds its own
    branch here; every call site elsewhere just calls the interface."""
    from app.core.config import get_settings

    adapter_name = get_settings().payment_adapter
    if adapter_name == "mock":
        return MockPaymentAdapter()
    raise ValueError(f"Unknown payment adapter: {adapter_name!r}")
