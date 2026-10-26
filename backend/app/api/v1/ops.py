"""P10-S02: operator-only endpoints, mounted at /internal (NOT under /api/v1).

`GET /internal/metrics` exposes Prometheus metrics. It is meant for a scraper on the
private network: the production proxy forwards only `/api/` and the web app, so it is
unreachable from the internet, and it is additionally bearer-token protected. Outside
local development it does not exist at all (404) until METRICS_TOKEN is configured.
"""
import hmac

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.core import metrics
from app.core.config import get_settings

router = APIRouter(prefix="/internal", tags=["ops"], include_in_schema=False)


@router.get("/metrics")
async def prometheus_metrics(request: Request):
    settings = get_settings()
    token = settings.metrics_token.get_secret_value()
    if not token:
        if not settings.is_local:
            raise HTTPException(status_code=404, detail="Not found")
    else:
        header = request.headers.get("Authorization", "")
        supplied = header[7:] if header.lower().startswith("bearer ") else ""
        if not hmac.compare_digest(supplied.encode(), token.encode()):
            raise HTTPException(status_code=401, detail="Metrics token required.")
    metrics.set_gauge("his_app_info", 1.0, {"version": settings.app_version, "environment": settings.environment})
    return PlainTextResponse(metrics.render(), media_type="text/plain; version=0.0.4")
