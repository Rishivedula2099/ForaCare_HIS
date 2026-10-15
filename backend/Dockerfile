# Multi-stage build: compile dependencies in a full image, run in a slim one.
FROM python:3.11-slim AS builder

WORKDIR /build
# P9-B06: install exactly the audited, hash-pinned set from requirements.lock
# (pyproject.toml uses ">=" ranges, so building from it would pull whatever is
# newest that day - unreproducible, and unscannable before it ships).
# Regenerate with infra/security/update-backend-lock.sh.
COPY requirements.lock ./

RUN pip install --no-cache-dir --require-hashes --prefix=/install -r requirements.lock


FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

COPY --from=builder /install /usr/local

# P7-B03: headless Chromium (plus its OS libraries) for HTML -> PDF. Installed
# to a shared path so the non-root runtime user can launch it; the sandbox is
# disabled because it cannot start in an unprivileged container - the browser
# only ever renders our own autoescaped, network-blocked HTML.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PDF_CHROMIUM_NO_SANDBOX=true
RUN playwright install --with-deps chromium \
    && chmod -R a+rX /ms-playwright \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini

# P9-B05: created before the chown so the named storage volume inherits appuser ownership.
RUN mkdir -p /app/storage && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header", "--no-proxy-headers"]
