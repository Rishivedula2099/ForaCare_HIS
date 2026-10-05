import uuid

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.permissions import require_permissions
from app.core.responses import ApiResponse, success_response
from app.modules.auth.models import User
from app.modules.lab import service
from app.modules.lab.report_pdf import build_lab_report_pdf
from app.modules.lab.schemas import (
    AccessionCreateRequest,
    ApproveResultsRequest,
    LabOrderStatusUpdateRequest,
    ParameterCreateRequest,
    ParameterUpdateRequest,
    ReferenceRangeCreateRequest,
    ReferenceRangeUpdateRequest,
    RejectApprovalRequest,
    RejectVerificationRequest,
    ResultAmendRequest,
    ResultEntryRequest,
    SampleCollectRequest,
    SampleMarkCollectedRequest,
    SampleRejectRequest,
    TestCreateRequest,
    TestUpdateRequest,
    VerifyResultsRequest,
)

router = APIRouter(prefix="/lab", tags=["lab"])


def _ok(request: Request, data):
    return success_response(data, request_id=getattr(request.state, "request_id", None))


# ---------------------------------------------------------------------------
# Test master (P6-F01)
# ---------------------------------------------------------------------------


@router.get("/tests", response_model=ApiResponse, summary="List/search lab tests")
async def list_tests(
    request: Request,
    name: str | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    tests = await service.list_tests(db, current_user, name=name, is_active=is_active)
    return _ok(request, [item.model_dump(mode="json") for item in tests])


@router.get("/tests/{test_id}", response_model=ApiResponse, summary="Get a single lab test")
async def get_test(
    test_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    item = await service.get_test(db, test_id, current_user)
    return _ok(request, item.model_dump(mode="json"))


@router.post("/tests", response_model=ApiResponse, summary="Create a lab test")
async def create_test(
    payload: TestCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.manage_master")),
):
    item = await service.create_test(db, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))


@router.patch("/tests/{test_id}", response_model=ApiResponse, summary="Update a lab test")
async def update_test(
    test_id: uuid.UUID,
    payload: TestUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.manage_master")),
):
    item = await service.update_test(db, test_id, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Parameter master (nested under a Test)
# ---------------------------------------------------------------------------


@router.get(
    "/tests/{test_id}/parameters", response_model=ApiResponse, summary="List parameters for a lab test"
)
async def list_parameters(
    test_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    parameters = await service.list_parameters(db, test_id, current_user)
    return _ok(request, [item.model_dump(mode="json") for item in parameters])


@router.get("/parameters/{parameter_id}", response_model=ApiResponse, summary="Get a single lab parameter")
async def get_parameter(
    parameter_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    item = await service.get_parameter(db, parameter_id, current_user)
    return _ok(request, item.model_dump(mode="json"))


@router.post(
    "/tests/{test_id}/parameters", response_model=ApiResponse, summary="Add a parameter to a lab test"
)
async def create_parameter(
    test_id: uuid.UUID,
    payload: ParameterCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.manage_master")),
):
    item = await service.create_parameter(db, test_id, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))


@router.patch("/parameters/{parameter_id}", response_model=ApiResponse, summary="Update a lab parameter")
async def update_parameter(
    parameter_id: uuid.UUID,
    payload: ParameterUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.manage_master")),
):
    item = await service.update_parameter(db, parameter_id, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# ReferenceRange master (nested under a Parameter)
# ---------------------------------------------------------------------------


@router.get(
    "/parameters/{parameter_id}/reference-ranges",
    response_model=ApiResponse,
    summary="List reference ranges for a lab parameter",
)
async def list_reference_ranges(
    parameter_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    ranges = await service.list_reference_ranges(db, parameter_id, current_user)
    return _ok(request, [item.model_dump(mode="json") for item in ranges])


@router.post(
    "/parameters/{parameter_id}/reference-ranges",
    response_model=ApiResponse,
    summary="Add a reference range to a lab parameter",
)
async def create_reference_range(
    parameter_id: uuid.UUID,
    payload: ReferenceRangeCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.manage_master")),
):
    item = await service.create_reference_range(db, parameter_id, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))


@router.patch(
    "/reference-ranges/{reference_range_id}",
    response_model=ApiResponse,
    summary="Update a reference range",
)
async def update_reference_range(
    reference_range_id: uuid.UUID,
    payload: ReferenceRangeUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.manage_master")),
):
    item = await service.update_reference_range(db, reference_range_id, payload, current_user)
    return _ok(request, item.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# LabOrder (P6-B02 state machine)
# ---------------------------------------------------------------------------


@router.get("/orders", response_model=ApiResponse, summary="List/filter lab orders")
async def list_lab_orders(
    request: Request,
    patient_id: uuid.UUID | None = None,
    status: str | None = None,
    accession_id: uuid.UUID | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    orders = await service.list_lab_orders(
        db, current_user, patient_id=patient_id, status=status, accession_id=accession_id
    )
    return _ok(request, [item.model_dump(mode="json") for item in orders])


@router.get("/orders/{lab_order_id}", response_model=ApiResponse, summary="Get a single lab order")
async def get_lab_order(
    lab_order_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    item = await service.get_lab_order(db, lab_order_id, current_user)
    return _ok(request, item.model_dump(mode="json"))


@router.get(
    "/orders/{lab_order_id}/status-history",
    response_model=ApiResponse,
    summary="List a lab order's status transition history",
)
async def list_lab_order_status_history(
    lab_order_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    history = await service.list_lab_order_status_history(db, lab_order_id, current_user)
    return _ok(request, [item.model_dump(mode="json") for item in history])


@router.patch(
    "/orders/{lab_order_id}/status",
    response_model=ApiResponse,
    summary="Transition a lab order to a new status",
)
async def transition_lab_order_status(
    lab_order_id: uuid.UUID,
    payload: LabOrderStatusUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    item = await service.transition_lab_order_status(
        db, current_user, lab_order_id, payload.status, remarks=payload.remarks
    )
    return _ok(request, item.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Accession / Sample (P6-B03 barcode generation, validation, resolution)
# ---------------------------------------------------------------------------


@router.post("/accessions", response_model=ApiResponse, summary="Accession a batch of billed lab orders")
async def create_accession(
    payload: AccessionCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.accession_sample")),
):
    item = await service.create_accession(db, current_user, payload)
    return _ok(request, item.model_dump(mode="json"))


@router.get("/accessions/{accession_id}", response_model=ApiResponse, summary="Get a single accession")
async def get_accession(
    accession_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    item = await service.get_accession(db, accession_id, current_user)
    return _ok(request, item.model_dump(mode="json"))


@router.post(
    "/accessions/{accession_id}/samples",
    response_model=ApiResponse,
    summary="Generate a tube barcode under an accession",
)
async def collect_sample(
    accession_id: uuid.UUID,
    payload: SampleCollectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.accession_sample")),
):
    item = await service.collect_sample(db, current_user, accession_id, payload)
    return _ok(request, item.model_dump(mode="json"))


@router.get("/samples/{sample_id}", response_model=ApiResponse, summary="Get a single sample")
async def get_sample(
    sample_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    item = await service.get_sample(db, sample_id, current_user)
    return _ok(request, item.model_dump(mode="json"))


@router.patch(
    "/samples/{sample_id}/collect",
    response_model=ApiResponse,
    summary="Mark a tube as physically collected",
)
async def mark_sample_collected(
    sample_id: uuid.UUID,
    payload: SampleMarkCollectedRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.accession_sample")),
):
    item = await service.mark_sample_collected(db, current_user, sample_id, remarks=payload.remarks)
    return _ok(request, item.model_dump(mode="json"))


@router.patch(
    "/samples/{sample_id}/reject",
    response_model=ApiResponse,
    summary="Reject a sample (e.g. mislabeled, hemolyzed, insufficient quantity)",
)
async def reject_sample(
    sample_id: uuid.UUID,
    payload: SampleRejectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.accession_sample")),
):
    item = await service.reject_sample(db, current_user, sample_id, reason=payload.reason)
    return _ok(request, item.model_dump(mode="json"))


@router.patch(
    "/samples/{sample_id}/process",
    response_model=ApiResponse,
    summary="Mark a sample received at the testing lab",
)
async def process_sample(
    sample_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.accession_sample")),
):
    item = await service.process_sample(db, current_user, sample_id)
    return _ok(request, item.model_dump(mode="json"))


@router.get(
    "/samples/{sample_id}/status-history",
    response_model=ApiResponse,
    summary="List a sample's status transition history",
)
async def list_sample_status_history(
    sample_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    history = await service.list_sample_status_history(db, sample_id, current_user)
    return _ok(request, [item.model_dump(mode="json") for item in history])


@router.get(
    "/barcode/{code}",
    response_model=ApiResponse,
    summary="Resolve a scanned accession/sample barcode to its record",
)
async def resolve_barcode(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    item = await service.resolve_barcode(db, current_user, code)
    return _ok(request, item.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Result (P6-B05 result engine / P6-F05 result entry)
# ---------------------------------------------------------------------------


@router.get(
    "/orders/{lab_order_id}/result-entry",
    response_model=ApiResponse,
    summary="Get the dynamic result-entry form for a lab order",
)
async def get_result_entry_form(
    lab_order_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    item = await service.get_result_entry_form(db, current_user, lab_order_id)
    return _ok(request, item.model_dump(mode="json"))


@router.post(
    "/orders/{lab_order_id}/results",
    response_model=ApiResponse,
    summary="Enter results for every parameter of a lab order's test",
)
async def enter_results(
    lab_order_id: uuid.UUID,
    payload: ResultEntryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.enter_results")),
):
    items = await service.enter_results(db, current_user, lab_order_id, payload)
    return _ok(request, [item.model_dump(mode="json") for item in items])


@router.get(
    "/orders/{lab_order_id}/results",
    response_model=ApiResponse,
    summary="List the entered results for a lab order",
)
async def list_results(
    lab_order_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    items = await service.list_results(db, current_user, lab_order_id)
    return _ok(request, [item.model_dump(mode="json") for item in items])


@router.get(
    "/results/{result_id}/versions",
    response_model=ApiResponse,
    summary="List a result's revision history",
)
async def list_result_versions(
    result_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    items = await service.list_result_versions(db, current_user, result_id)
    return _ok(request, [item.model_dump(mode="json") for item in items])


@router.patch(
    "/results/{result_id}/amend",
    response_model=ApiResponse,
    summary="Amend a result on an already-approved/finalized order",
)
async def amend_result(
    result_id: uuid.UUID,
    payload: ResultAmendRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.approve_reports")),
):
    item = await service.amend_result(
        db, current_user, result_id, value=payload.value, unit=payload.unit, reason=payload.reason
    )
    return _ok(request, item.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Verification / Approval (P6-F06 technician workflow, technical
# verification, authorized approval, finalization)
# ---------------------------------------------------------------------------


@router.post(
    "/orders/{lab_order_id}/verify",
    response_model=ApiResponse,
    summary="Technically verify a lab order's results and queue it for approval",
)
async def verify_results(
    lab_order_id: uuid.UUID,
    payload: VerifyResultsRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.verify_results")),
):
    item = await service.verify_results(db, current_user, lab_order_id, remarks=payload.remarks)
    return _ok(request, item.model_dump(mode="json"))


@router.post(
    "/orders/{lab_order_id}/verify/reject",
    response_model=ApiResponse,
    summary="Reject technical verification and send results back for correction",
)
async def reject_verification(
    lab_order_id: uuid.UUID,
    payload: RejectVerificationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.verify_results")),
):
    item = await service.reject_verification(db, current_user, lab_order_id, reason=payload.reason)
    return _ok(request, item.model_dump(mode="json"))


@router.get(
    "/orders/{lab_order_id}/verifications",
    response_model=ApiResponse,
    summary="List a lab order's verification history",
)
async def list_verifications(
    lab_order_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    items = await service.list_verifications(db, current_user, lab_order_id)
    return _ok(request, [item.model_dump(mode="json") for item in items])


@router.post(
    "/orders/{lab_order_id}/approve",
    response_model=ApiResponse,
    summary="Give final authorized approval to a lab order's results",
)
async def approve_results(
    lab_order_id: uuid.UUID,
    payload: ApproveResultsRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.approve_reports")),
):
    item = await service.approve_results(db, current_user, lab_order_id, remarks=payload.remarks)
    return _ok(request, item.model_dump(mode="json"))


@router.post(
    "/orders/{lab_order_id}/approve/reject",
    response_model=ApiResponse,
    summary="Reject approval and send results back for correction",
)
async def reject_approval(
    lab_order_id: uuid.UUID,
    payload: RejectApprovalRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.approve_reports")),
):
    item = await service.reject_approval(db, current_user, lab_order_id, reason=payload.reason)
    return _ok(request, item.model_dump(mode="json"))


@router.get(
    "/orders/{lab_order_id}/approvals",
    response_model=ApiResponse,
    summary="List a lab order's approval history",
)
async def list_approvals(
    lab_order_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    items = await service.list_approvals(db, current_user, lab_order_id)
    return _ok(request, [item.model_dump(mode="json") for item in items])


@router.post(
    "/orders/{lab_order_id}/finalize",
    response_model=ApiResponse,
    summary="Finalize an approved lab order (seals the report)",
)
async def finalize_order(
    lab_order_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.approve_reports")),
):
    item = await service.finalize_order(db, current_user, lab_order_id)
    return _ok(request, item.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Report (P6-F07 lab report UI)
# ---------------------------------------------------------------------------


@router.get(
    "/orders/{lab_order_id}/report",
    response_model=ApiResponse,
    summary="Get the full lab report for an APPROVED/FINALIZED order",
)
async def get_lab_report(
    lab_order_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    item = await service.get_lab_report(db, current_user, lab_order_id)
    return _ok(request, item.model_dump(mode="json"))


@router.get(
    "/orders/{lab_order_id}/report.pdf",
    summary="Download the lab report as a generated PDF (P6-B08)",
)
async def get_lab_report_pdf(
    lab_order_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("lab.view")),
):
    report = await service.get_lab_report(db, current_user, lab_order_id)
    verify_url = (
        f"{request.base_url}api/v1/lab/verify-doc?id={report.lab_order_id}&sig={report.report_qr_token}"
        if report.report_qr_token
        else None
    )
    pdf_bytes = build_lab_report_pdf(report, verify_url=verify_url)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{report.order_number}.pdf"'},
    )


@router.get(
    "/verify-doc",
    response_model=ApiResponse,
    summary="Public, unauthenticated verification of a lab report's QR code",
)
async def verify_lab_report(
    request: Request,
    id: uuid.UUID,
    sig: str,
    db: AsyncSession = Depends(get_db),
):
    item = await service.verify_lab_report(db, id, sig)
    return _ok(request, item.model_dump(mode="json"))
