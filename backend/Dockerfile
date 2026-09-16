# Multi-stage build: compile dependencies in a full image, run in a slim one.
FROM python:3.11-slim AS builder

WORKDIR /build
COPY pyproject.toml ./

# Dependencies are declared once in pyproject.toml ([project.dependencies]) -
# extract them at build time instead of duplicating the list here so the
# image never drifts from what the app actually depends on.
RUN python -c "import tomllib; deps = tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']; open('requirements.txt', 'w').write('\n'.join(deps))"

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

COPY --from=builder /install /usr/local

WORKDIR /app
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
