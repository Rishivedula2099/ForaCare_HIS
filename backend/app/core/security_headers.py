"""P9-B01: baseline security headers on every API response."""
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings

# Swagger/ReDoc load scripts from a CDN, so the strict API CSP only applies
# to everything else (the docs routes are disabled outside local anyway).
_DOC_PATHS = ("/docs", "/redoc", "/openapi.json")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        headers = response.headers
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "no-referrer")
        headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
        if not request.url.path.startswith(_DOC_PATHS):
            headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
            # Clinical data and session responses must never sit in a shared cache.
            headers.setdefault("Cache-Control", "no-store")
        if not get_settings().is_local:
            headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response
