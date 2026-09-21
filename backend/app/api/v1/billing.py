import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permissions
from app.core.responses import ApiResponse, success_response
from app.modules.auth.models import User
from app.modules.billing import service
from app.modules.billing.schemas import (
    DepositCreateRequest,
    InvoiceCreateRequest,
    PackageCreateRequest,
    PackageUpdateRequest,
    PaymentCreateRequest,
    RefundCreateRequest,
    ServiceCreateRequest,
    ServiceUpdateRequest,
)

router = APIRouter(prefix="/billing", tags=["billing"])


def _ok(request: Request, data):
    return success_response(data, request_id=getattr(request.state, "request_id", None))


# ---------------------------------------------------------------------------
# Service master
# ---------------------------------------------------------------------------


@router.get("/services", response_model=ApiResponse, summary="List/search billing services")
async def list_services(
    request: Request,
    name: str | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("billing.view_services")),
):
    services = await service.list_services(db, current_user, name=name, is_active=is_active)
    return _ok(request, [item.model_dump(mode="json") for item in services])


@router.get("/services/{service_id}", response_model=ApiResponse, summary="Get a single billing service")
async def get_service(
    service_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("billing.view_services")),
):
    item = await service.get_service(db, service_id, current_user)
    return _ok(request, item.model_dump(mode="json"))


@router.post("/services", response_model=ApiResponse, summary="Create a billing service")
async def create_service(
    payload: ServiceCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("billing.manage_services")),
):
    item = await service.create_service(db, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))


@router.patch("/services/{service_id}", response_model=ApiResponse, summary="Update a billing service")
async def update_service(
    service_id: uuid.UUID,
    payload: ServiceUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("billing.manage_services")),
):
    item = await service.update_service(db, service_id, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Package master
# ---------------------------------------------------------------------------


@router.get("/packages", response_model=ApiResponse, summary="List/search billing packages")
async def list_packages(
    request: Request,
    name: str | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("billing.view_services")),
):
    packages = await service.list_packages(db, current_user, name=name, is_active=is_active)
    return _ok(request, [item.model_dump(mode="json") for item in packages])


@router.get("/packages/{package_id}", response_model=ApiResponse, summary="Get a single billing package")
async def get_package(
    package_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("billing.view_services")),
):
    item = await service.get_package(db, package_id, current_user)
    return _ok(request, item.model_dump(mode="json"))


@router.post("/packages", response_model=ApiResponse, summary="Create a billing package")
async def create_package(
    payload: PackageCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("billing.manage_services")),
):
    item = await service.create_package(db, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))


@router.patch("/packages/{package_id}", response_model=ApiResponse, summary="Update a billing package")
async def update_package(
    package_id: uuid.UUID,
    payload: PackageUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("billing.manage_services")),
):
    item = await service.update_package(db, package_id, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------


@router.get("/invoices", response_model=ApiResponse, summary="List/search invoices")
async def list_invoices(
    request: Request,
    patient_id: uuid.UUID | None = None,
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("billing.view_invoices")),
):
    invoices = await service.list_invoices(db, current_user, patient_id=patient_id, status=status)
    return _ok(request, [item.model_dump(mode="json") for item in invoices])


@router.get("/invoices/{invoice_id}", response_model=ApiResponse, summary="Get a single invoice")
async def get_invoice(
    invoice_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("billing.view_invoices")),
):
    item = await service.get_invoice(db, invoice_id, current_user)
    return _ok(request, item.model_dump(mode="json"))


@router.post("/invoices", response_model=ApiResponse, summary="Create an invoice")
async def create_invoice(
    payload: InvoiceCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("billing.create_invoice")),
):
    item = await service.create_invoice(db, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------


@router.get(
    "/invoices/{invoice_id}/payments", response_model=ApiResponse, summary="List payments on an invoice"
)
async def list_payments(
    invoice_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("billing.view_invoices")),
):
    payments = await service.list_payments(db, invoice_id, current_user)
    return _ok(request, [item.model_dump(mode="json") for item in payments])


@router.post(
    "/invoices/{invoice_id}/payments",
    response_model=ApiResponse,
    summary="Record a payment against an invoice",
)
async def record_payment(
    invoice_id: uuid.UUID,
    payload: PaymentCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("billing.collect_payment")),
):
    item = await service.record_payment(db, invoice_id, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Deposit
# ---------------------------------------------------------------------------


@router.get("/deposits", response_model=ApiResponse, summary="List/search patient deposits")
async def list_deposits(
    request: Request,
    patient_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("billing.view_invoices")),
):
    deposits = await service.list_deposits(db, current_user, patient_id=patient_id)
    return _ok(request, [item.model_dump(mode="json") for item in deposits])


@router.post("/deposits", response_model=ApiResponse, summary="Record a patient deposit")
async def record_deposit(
    payload: DepositCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("billing.collect_payment")),
):
    item = await service.record_deposit(db, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Refund
# ---------------------------------------------------------------------------


@router.post("/refunds", response_model=ApiResponse, summary="Refund a payment or deposit")
async def create_refund(
    payload: RefundCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("billing.refund")),
):
    item = await service.create_refund(db, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------


@router.get("/receipts/{receipt_id}", response_model=ApiResponse, summary="Get a single receipt")
async def get_receipt(
    receipt_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("billing.view_invoices")),
):
    item = await service.get_receipt(db, receipt_id, current_user)
    return _ok(request, item.model_dump(mode="json"))
