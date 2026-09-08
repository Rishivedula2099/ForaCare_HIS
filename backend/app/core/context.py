import uuid
from contextvars import ContextVar

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
_tenant_id_ctx: ContextVar[uuid.UUID | None] = ContextVar("tenant_id", default=None)
_facility_id_ctx: ContextVar[uuid.UUID | None] = ContextVar("facility_id", default=None)
_actor_user_id_ctx: ContextVar[uuid.UUID | None] = ContextVar("actor_user_id", default=None)


def set_request_id(request_id: str) -> None:
    _request_id_ctx.set(request_id)


def get_request_id() -> str | None:
    return _request_id_ctx.get()


def set_tenant_context(
    *, tenant_id: uuid.UUID, facility_id: uuid.UUID | None, actor_user_id: uuid.UUID
) -> None:
    """Records the authenticated request's tenant/facility/actor for this task.

    Set once per request (from `get_current_user`) so anything downstream -
    tenant-scoped queries, audit logging - can read it without threading the
    current user through every function signature. Starlette runs each async
    request in its own asyncio task, so ContextVar state never leaks across
    concurrent requests.
    """
    _tenant_id_ctx.set(tenant_id)
    _facility_id_ctx.set(facility_id)
    _actor_user_id_ctx.set(actor_user_id)


def get_current_tenant_id() -> uuid.UUID | None:
    return _tenant_id_ctx.get()


def get_current_facility_id() -> uuid.UUID | None:
    return _facility_id_ctx.get()


def get_current_actor_user_id() -> uuid.UUID | None:
    return _actor_user_id_ctx.get()
