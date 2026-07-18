"""HTTP middleware wiring: security response headers and CORS.

Configured once from `app.main`. Kept to Starlette/FastAPI built-ins so no
new dependency is introduced.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.config import get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add conservative, always-safe security headers to every response.

    A Content-Security-Policy is deliberately NOT set here: the server-rendered
    Persian panels would need per-page nonces to keep a strict policy working,
    so CSP is left as scoped future work rather than shipped half-configured.
    HSTS is only advertised once the deployment is actually on HTTPS
    (`COOKIE_SECURE=true`), to avoid pinning browsers to HTTPS during local
    HTTP development.
    """

    def __init__(self, app: ASGIApp, hsts: bool = False) -> None:
        super().__init__(app)
        self._hsts = hsts

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        if self._hsts:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


def configure_middleware(app: FastAPI) -> None:
    """Attach CORS (only when origins are configured) and security headers."""
    settings = get_settings()
    origins = settings.cors_origin_list
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.cookie_secure)
