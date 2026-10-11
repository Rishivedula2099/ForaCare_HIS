"""P7-B06: authorization-before-generation and audit of document access.

Engine-level unit tests with stubbed loaders/renderers and a recording audit
service - no database or browser needed.
"""
import uuid
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.core.exceptions import ForbiddenError, NotFoundError
from app.modules.documents import service
from app.modules.documents.base import DocumentSpec, PreparedDocument

TENANT = uuid.uuid4()
FACILITY = uuid.uuid4()


def make_user(*perms, facility=FACILITY):
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=TENANT,
        facility_id=facility,
        role=SimpleNamespace(permissions=[SimpleNamespace(code=c) for c in perms]),
    )


class FakeDB:
    def __init__(self):
        self.rollbacks = 0

    async def rollback(self):
        self.rollbacks += 1


@pytest.fixture
def env(monkeypatch):
    state = SimpleNamespace(loads=0, renders=0, audit=[], loader=None)

    async def default_loader(db, resource_id, user):
        return PreparedDocument(TENANT, FACILITY, 'RCP/../1"x', {}, reference="RCP-1")

    state.loader = default_loader

    async def load(db, resource_id, user):
        state.loads += 1
        return await state.loader(db, resource_id, user)

    async def render(db, doc, ctx):
        state.renders += 1
        return b"%PDF-fake"

    async def record_event(db, **kwargs):
        state.audit.append(kwargs)

    spec = DocumentSpec("RECEIPT", "Receipt", ("billing.view",), "receipt", load, render)
    monkeypatch.setattr(service, "_REGISTRY", {"RECEIPT": spec})
    monkeypatch.setattr(service.audit_service, "record_event", record_event)
    return state


ALL = ("documents.print", "billing.view")


async def test_missing_print_permission_is_refused_before_anything_loads(env):
    user = make_user("billing.view")  # module access only
    with pytest.raises(ForbiddenError):
        await service.generate_document(FakeDB(), "RECEIPT", uuid.uuid4(), user)
    assert env.loads == 0 and env.renders == 0
    [event] = env.audit
    assert event["action"] == "document.access_denied"
    assert event["after"]["missing_permissions"] == ["documents.print"]
    assert event["actor_user_id"] == user.id


async def test_missing_module_permission_is_refused_before_anything_loads(env):
    with pytest.raises(ForbiddenError):
        await service.generate_document(FakeDB(), "RECEIPT", uuid.uuid4(), make_user("documents.print"))
    assert env.loads == 0
    assert env.audit[0]["after"]["missing_permissions"] == ["billing.view"]


async def test_other_facilitys_document_is_not_found_and_audited(env):
    async def other_facility(db, resource_id, user):
        return PreparedDocument(TENANT, uuid.uuid4(), "R", {})  # a loader that forgot its own check

    env.loader = other_facility
    db = FakeDB()
    with pytest.raises(NotFoundError):
        await service.generate_document(db, "RECEIPT", uuid.uuid4(), make_user(*ALL))
    assert env.renders == 0 and db.rollbacks == 1
    [event] = env.audit
    assert event["action"] == "document.generation_failed"
    assert event["after"]["error_code"] == NotFoundError.code


async def test_loader_error_is_audited_and_reraised(env):
    async def boom(db, resource_id, user):
        raise NotFoundError("Receipt not found.")

    env.loader = boom
    with pytest.raises(NotFoundError):
        await service.generate_document(FakeDB(), "RECEIPT", uuid.uuid4(), make_user(*ALL), access={"client_ip": "1.2.3.4"})
    assert env.audit[0]["action"] == "document.generation_failed"
    assert env.audit[0]["after"]["client_ip"] == "1.2.3.4"


async def test_unexpected_error_is_audited_as_internal(env):
    async def crash(db, resource_id, user):
        raise RuntimeError("db exploded")

    env.loader = crash
    with pytest.raises(RuntimeError):
        await service.generate_document(FakeDB(), "RECEIPT", uuid.uuid4(), make_user(*ALL))
    assert env.audit[0]["after"]["error_code"] == "INTERNAL_ERROR"


async def test_success_is_audited_with_delivery_details_and_safe_filename(env):
    rid = uuid.uuid4()
    doc = await service.generate_document(
        FakeDB(), "receipt", rid, make_user(*ALL), access={"disposition": "attachment", "client_ip": "10.0.0.1"}
    )
    assert doc.content == b"%PDF-fake"
    assert doc.filename == "RCP_._1_x.pdf"
    assert '"' not in doc.filename and "/" not in doc.filename and ".." not in doc.filename
    [event] = env.audit
    assert event["action"] == "document.generated"
    assert event["resource_id"] == rid
    assert event["after"]["disposition"] == "attachment"
    assert event["after"]["client_ip"] == "10.0.0.1"
    assert event["after"]["size_bytes"] == len(b"%PDF-fake")


def test_document_types_hide_what_the_caller_cannot_print(env):
    assert service.list_document_types(make_user("billing.view")) == []  # no print permission
    assert service.list_document_types(make_user("documents.print")) == []  # no module permission
    assert [t.code for t in service.list_document_types(make_user(*ALL))] == ["RECEIPT"]


@pytest.mark.parametrize(
    "raw, expected",
    [("RCP-2026-1", "RCP-2026-1"), ('a"b/c\\d', "a_b_c_d"), ("../../etc/passwd", "etc_passwd"), ("", "document"), ("é\r\nX", "X")],
)
def test_safe_filename(raw, expected):
    assert service.safe_filename(raw) == expected
