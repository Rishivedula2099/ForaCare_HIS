# ForaCare HIS Backend

FastAPI foundation for the ForaCare HIS backend (task P1-B01).

## Setup

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows
pip install -e ".[dev]"
cp .env.example .env
```

### Database (local)

```bash
docker compose up -d   # starts PostgreSQL 16 on localhost:5432
```

Adjust `DATABASE_URL` and the `DB_*` pool settings in `.env` to point elsewhere (e.g. a managed Postgres instance).

## Run

```bash
uvicorn app.main:app --reload
```

Liveness: `GET http://localhost:8000/api/v1/health`
Readiness (checks DB pool): `GET http://localhost:8000/api/v1/health/db`

## Test

```bash
pytest
```

## Layout

- `app/main.py` — app factory, middleware and router wiring
- `app/core/config.py` — environment-driven settings (`Settings`, `get_settings()`)
- `app/core/logging.py` — logging setup, request-ID aware formatter
- `app/core/middleware.py` — correlation ID middleware (`X-Request-ID`)
- `app/core/exceptions.py` — `AppError` hierarchy and global exception handlers
- `app/core/responses.py` — standard success/error response envelopes
- `app/core/database.py` — async SQLAlchemy 2.0 engine/pool, `SessionLocal`, `get_db()` dependency
- `app/api/v1/` — versioned API routes, mounted under `/api/v1`

## Database session usage

Depend on `get_db` in a route/service to get a request-scoped `AsyncSession`:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

@router.get("/patients/{patient_id}")
async def get_patient(patient_id: str, db: AsyncSession = Depends(get_db)):
    ...
```

ORM models should subclass `app.core.database.Base`. Pool sizing is controlled via `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`, and `DB_POOL_RECYCLE`.

## Migrations (Alembic)

Migrations live under `migrations/versions/`. `migrations/env.py` reads `DATABASE_URL` from `app.core.config.get_settings()` (same source as the app), so there is nothing to configure separately for migrations — set `.env` once.

### Running migrations

```bash
alembic upgrade head        # apply all pending migrations
alembic downgrade -1        # roll back the last migration
alembic current             # show the currently applied revision
alembic history              # list all revisions
```

### Authoring a migration

1. Define/change your SQLAlchemy models under `app/modules/<module>/models.py`, subclassing `app.core.database.Base`.
2. Add an import for that module's `models` in `migrations/env.py` (see the comment near the top) so autogenerate can see its tables.
3. Generate a revision:
   ```bash
   alembic revision --autogenerate -m "add patient table"
   ```
4. **Read the generated file.** Autogenerate does not detect everything (e.g. column renames show up as drop+add, some check constraints, server-side defaults) — verify `upgrade()`/`downgrade()` are both correct and symmetric before committing.
5. Apply it locally (`alembic upgrade head`) and confirm the app still boots and `GET /api/v1/health/db` returns ok.

### Conventions

- One logical schema change per migration; do not bundle unrelated table changes together.
- Every migration must implement a working `downgrade()` — no `pass`-only downgrades once real schema changes are involved.
- Constraints/indexes get deterministic names via the `NAMING_CONVENTION` in `app/core/database.py` (`ix_`, `uq_`, `ck_`, `fk_`, `pk_` prefixes) so autogenerate diffs stay stable across environments instead of using dialect-generated hash names.
- File names are timestamp-prefixed (`YYYYMMDD_HHMM_<revision>_<slug>.py`, see `alembic.ini`'s `file_template`) so `ls migrations/versions` reads in chronological order.
- Never edit or delete a migration that has already been applied anywhere outside your own machine — add a new migration instead.
- Migrations are applied manually (`alembic upgrade head`) as an explicit deployment step, not automatically on app startup, so a bad migration never blocks the API from starting for unrelated reasons.
- `alembic upgrade head --sql` prints the DDL without connecting to a database — useful for reviewing a migration in CI or handing SQL to a DBA.

## Conventions

Every `/api/v1` response is wrapped in a standard envelope:

```json
{ "success": true, "data": { ... }, "error": null, "meta": { "request_id": "...", "timestamp": "..." } }
```

```json
{ "success": false, "data": null, "error": { "code": "NOT_FOUND", "message": "...", "details": [] }, "meta": { "request_id": "...", "timestamp": "..." } }
```

Raise `app.core.exceptions.AppError` (or its subclasses `NotFoundError`, `ConflictError`, `UnauthorizedError`, `ForbiddenError`) from route/service code to get the standard error envelope automatically. Unhandled exceptions and validation errors are also normalized to this shape.

Every request receives an `X-Request-ID` (reused from the incoming header if present), which is threaded through logs and the response `meta.request_id`.
