import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1 import api_v1_router
from app.core.config import get_settings
from app.core.database import dispose_engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.modules.documents.playwright_pdf import shutdown_pdf_engine
from app.core.http_security import (
    HttpsOnlyMiddleware,
    RequestSizeLimitMiddleware,
    SameOriginWritesMiddleware,
    TrustedProxyMiddleware,
)
from app.core.middleware import CorrelationIdMiddleware
from app.core.security_headers import SecurityHeadersMiddleware

settings = get_settings()
configure_logging(settings)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("%s starting up (environment=%s)", settings.app_name, settings.environment)
    yield
    logger.info("%s shutting down", settings.app_name)
    await shutdown_pdf_engine()
    await dispose_engine()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
    # P9-B01: don't publish the API schema outside local development.
    docs_url="/docs" if settings.is_local else None,
    redoc_url="/redoc" if settings.is_local else None,
    openapi_url="/openapi.json" if settings.is_local else None,
)

# P10-S01: later add_middleware calls wrap earlier ones, so the list below
# reads innermost -> outermost. Outermost first at runtime:
#   TrustedHost -> TrustedProxy -> HttpsOnly -> CORS -> SecurityHeaders
#   -> CorrelationId -> RequestSizeLimit -> SameOriginWrites -> routes
app.add_middleware(SameOriginWritesMiddleware, trusted_origins=settings.cors_origin_list)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_request_body_bytes)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
if settings.https_enforced:
    app.add_middleware(HttpsOnlyMiddleware)
if settings.trusted_proxy_networks:
    app.add_middleware(TrustedProxyMiddleware, networks=settings.trusted_proxy_networks)
if settings.allowed_host_list and "*" not in settings.allowed_host_list:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list)

register_exception_handlers(app)

app.include_router(api_v1_router, prefix=settings.api_v1_prefix)
