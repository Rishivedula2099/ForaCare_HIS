import uuid
from dataclasses import asdict

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings
from app.core.permissions import get_current_user, require_permissions
from app.core.rate_limit import rate_limit
from app.core.responses import ApiResponse, success_response
from app.modules.auth.models import User
from app.modules.documents import service, templates
from app.modules.documents.schemas import (
    TemplateCreateRequest,
    TemplateUpdateRequest,
    TemplateVersionCreateRequest,
)
from app.modules.documents.service import DocumentContext

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/types", response_model=ApiResponse, summary="Document types the caller may generate")
async def list_document_types(request: Request, current_user: User = Depends(get_current_user)):
    items = [item.model_dump(mode="json") for item in service.list_document_types(current_user)]
    return success_response(items, request_id=getattr(request.state, "request_id", None))


@router.get(
    "/verify",
    response_model=ApiResponse,
    summary="Public, unauthenticated verification of a printed document QR code (P7-B05)",
    dependencies=[Depends(rate_limit("doc-verify", limit=get_settings().rate_limit_public_per_minute))],
)
async def verify_document(
    request: Request,
    t: str = Query(max_length=40),
    id: uuid.UUID = Query(),
    sig: str = Query(max_length=128),
    db: AsyncSession = Depends(get_db),
):
    result = await service.verify_document(db, t, id, sig)
    return success_response(asdict(result), request_id=getattr(request.state, "request_id", None))


# --- Templates (P7-B02). Declared before the generic "/{doc_type}/{resource_id}"
# route so "/templates/{id}" is not captured as a document type. ------------

_manage_templates = require_permissions("documents.manage_templates")


def _ok(request: Request, data):
    return success_response(data, request_id=getattr(request.state, "request_id", None))


@router.get("/templates", response_model=ApiResponse, summary="List this facility's document templates")
async def list_templates(
    request: Request,
    document_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_manage_templates),
):
    items = await templates.list_templates(db, current_user, document_type)
    return _ok(request, [item.model_dump(mode="json") for item in items])


@router.post("/templates", response_model=ApiResponse, summary="Create a template (as V1)")
async def create_template(
    payload: TemplateCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_manage_templates),
):
    return _ok(request, (await templates.create_template(db, payload, current_user)).model_dump(mode="json"))


@router.get("/templates/{template_id}", response_model=ApiResponse, summary="Get a template with all versions")
async def get_template(
    template_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_manage_templates),
):
    return _ok(request, (await templates.get_template(db, template_id, current_user)).model_dump(mode="json"))


@router.patch("/templates/{template_id}", response_model=ApiResponse, summary="Rename or (de)activate a template")
async def update_template(
    template_id: uuid.UUID,
    payload: TemplateUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_manage_templates),
):
    result = await templates.update_template(db, template_id, payload, current_user)
    return _ok(request, result.model_dump(mode="json"))


@router.post("/templates/{template_id}/versions", response_model=ApiResponse, summary="Add a new version (goes live)")
async def create_template_version(
    template_id: uuid.UUID,
    payload: TemplateVersionCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_manage_templates),
):
    result = await templates.create_version(db, template_id, payload, current_user)
    return _ok(request, result.model_dump(mode="json"))


@router.post(
    "/templates/{template_id}/versions/{version_number}/activate",
    response_model=ApiResponse,
    summary="Make an existing version the live one (rollback)",
)
async def activate_template_version(
    template_id: uuid.UUID,
    version_number: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_manage_templates),
):
    result = await templates.activate_version(db, template_id, version_number, current_user)
    return _ok(request, result.model_dump(mode="json"))


@router.get(
    "/{doc_type}/{resource_id}/history",
    response_model=ApiResponse,
    summary="Audit trail of who generated / was denied / failed to generate a document",
)
async def document_history(
    doc_type: str,
    resource_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions("audit.view_logs")),
):
    events = await service.list_document_events(db, doc_type, resource_id, current_user)
    return _ok(request, [event.model_dump(mode="json") for event in events])


@router.get(
    "/{doc_type}/{resource_id}",
    summary="Generate a document as PDF (permission + facility validated)",
)
async def generate_document(
    doc_type: str,
    resource_id: uuid.UUID,
    request: Request,
    download: bool = Query(default=False),
    template_version: int | None = Query(default=None, ge=1, description="Reproduce with this template version"),
    paper_size: str | None = Query(default=None, description="A4 | A5 | A6 | THERMAL_58 | THERMAL_80 | CUSTOM; overrides the template"),
    width_mm: float | None = Query(default=None, description="With paper_size=CUSTOM"),
    height_mm: float | None = Query(default=None, description="With paper_size=CUSTOM"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    disposition = "attachment" if download else "inline"
    document = await service.generate_document(
        db, doc_type, resource_id, current_user, DocumentContext(base_url=str(request.base_url)), template_version, paper_size,
        (width_mm, height_mm) if width_mm is not None and height_mm is not None else None,
        access={"disposition": disposition, "client_ip": request.client.host if request.client else None},
    )
    return Response(
        content=document.content,
        media_type=document.media_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{document.filename}"',
            # Documents contain patient data: never cache them in the browser
            # or a shared proxy, and never let the browser sniff another type.
            "Cache-Control": "no-store, private",
            "Pragma": "no-cache",
            "X-Content-Type-Options": "nosniff",
        },
    )
