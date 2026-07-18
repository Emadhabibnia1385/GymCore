"""GymCore FastAPI application entrypoint.

Serves:
  - REST API under /api/v1 (web, bots-adjacent tooling, future mobile app)
  - Persian RTL admin panel under /admin
  - Client dashboard under / (login) and /me
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app import __version__
from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.exceptions import (
    AuthError,
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationError,
)
from app.core.logging import setup_logging
from app.core.middleware import configure_middleware
from app.db.base import Base
from app.db.session import engine, session_scope
from app.web import admin as web_admin
from app.web import client as web_client
from app.web.deps import LoginRedirect

_STATUS_BY_EXCEPTION = {
    NotFoundError: 404,
    ValidationError: 422,
    AuthError: 401,
    ConflictError: 409,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    # v1 schema management: create missing tables on startup.
    # (Alembic migrations will take over once the schema starts evolving.)
    import app.models  # noqa: F401 — register all tables on Base.metadata

    Base.metadata.create_all(bind=engine)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    with session_scope() as db:
        from app.services import app_settings, auth

        app_settings.seed_defaults(db)
        auth.bootstrap_admin(db)
    yield


app = FastAPI(title="GymCore", version=__version__, lifespan=lifespan)
configure_middleware(app)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError):
    status_code = 400
    for exc_type, code in _STATUS_BY_EXCEPTION.items():
        if isinstance(exc, exc_type):
            status_code = code
            break
    # Web pages get redirected back with the error message; API gets JSON.
    if not request.url.path.startswith("/api/"):
        referer = request.headers.get("referer") or "/"
        return RedirectResponse(f"{referer.split('?')[0]}?error={exc}", status_code=303)
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


@app.exception_handler(LoginRedirect)
async def login_redirect_handler(request: Request, exc: LoginRedirect):
    return RedirectResponse(exc.target, status_code=303)


@app.get("/health", tags=["health"])
def health() -> dict:
    """Liveness probe — the process is up. Does not touch the database."""
    return {"status": "ok", "version": __version__}


@app.get("/health/ready", tags=["health"])
def readiness():
    """Readiness probe — verifies the database is reachable.

    Returns 503 (not 500) when the DB is down so orchestrators/load balancers
    can drain this instance instead of serving failing requests.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "version": __version__},
        )
    return {"status": "ready", "version": __version__}


app.include_router(api_router)
app.include_router(web_admin.router)
app.include_router(web_client.router)

_static_dir = Path(__file__).parent / "web" / "static"
app.mount("/static", StaticFiles(directory=_static_dir), name="static")
