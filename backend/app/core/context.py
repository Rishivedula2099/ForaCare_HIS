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
    note_request(user_id=actor_user_id, tenant_id=tenant_id, facility_id=facility_id)


def get_current_tenant_id() -> uuid.UUID | None:
    return _tenant_id_ctx.get()


def get_current_facility_id() -> uuid.UUID | None:
    return _facility_id_ctx.get()


def get_current_actor_user_id() -> uuid.UUID | None:
    return _actor_user_id_ctx.get()


# P10-S02: a mutable per-request holder. `get_current_user` runs in a child task
# (BaseHTTPMiddleware), so ContextVar writes made there are invisible to the
# access-log middleware; mutating this shared dict is not.
_request_state_ctx: ContextVar[dict | None] = ContextVar("request_state", default=None)


def init_request_state() -> dict:
    state: dict = {}
    _request_state_ctx.set(state)
    return state


def note_request(**fields) -> None:
    """Attach facts (user_id, tenant_id, ...) to the request's access-log line."""
    state = _request_state_ctx.get()
    if state is not None:
        state.update({k: str(v) for k, v in fields.items() if v is not None})
