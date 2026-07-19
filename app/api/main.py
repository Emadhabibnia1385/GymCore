"""GymCore internal FastAPI service.

This is NOT a user-facing dashboard — the entire product is the Telegram/Bale
bots. It exposes only:
  - liveness/readiness probes for orchestration
  - a small brand-styled status page at `/`
  - optional webhook receivers (used only when a bot runs in webhook mode;
    long polling is the default and needs none of this)

Bind loopback by default (APP_HOST=127.0.0.1); front with your own reverse proxy
only if you deliberately enable webhook mode.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import text
from starlette.concurrency import run_in_threadpool

from app import __version__
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.init import init_dev_schema
from app.db.session import engine, session_scope
from app.models import Platform
from app.services import bootstrap

_PLATFORMS = {"telegram": Platform.TELEGRAM, "bale": Platform.BALE}
_dispatchers: dict[Platform, object] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    init_dev_schema()
    with session_scope() as db:
        bootstrap.seed_all(db)
    yield


app = FastAPI(
    title="GymCore", version=__version__, lifespan=lifespan, docs_url=None, redoc_url=None
)

_STATUS_PAGE = """<!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GymCore</title><style>
:root{{--green:#B2F828;--black:#000;--white:#fff}}
*{{margin:0;box-sizing:border-box}}
body{{background:var(--black);color:var(--white);font-family:system-ui,sans-serif;
min-height:100vh;display:grid;place-items:center;text-align:center}}
.card{{padding:2.5rem 3rem;border:1px solid #222;border-radius:16px}}
h1{{color:var(--green);font-size:2rem;letter-spacing:.5px}}
.dot{{color:var(--green)}} .v{{opacity:.6;margin-top:.75rem;font-size:.85rem}}
p{{margin-top:.5rem}}
</style></head><body><div class="card">
<h1>GymCore</h1>
<p><span class="dot">●</span> سرویس فعال است</p>
<p class="v">v{version} — Mahdi Sarmad</p>
</div></body></html>"""


@app.get("/", include_in_schema=False)
def status_page() -> HTMLResponse:
    return HTMLResponse(_STATUS_PAGE.format(version=__version__))


@app.get("/health", tags=["health"])
def health() -> dict:
    """Liveness — the process is up. Does not touch the database."""
    return {"status": "ok", "version": __version__}


@app.get("/health/ready", tags=["health"])
def readiness():
    """Readiness — verifies the database is reachable (503 when it is not)."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return {"status": "ready", "version": __version__}


def _get_dispatcher(platform: Platform):
    """Lazily build and cache a dispatcher for webhook delivery."""
    from app.bots.common.client import build_client
    from app.bots.common.context import make_context
    from app.bots.common.router import Dispatcher

    if platform not in _dispatchers:
        client = build_client(platform)
        if client is None:
            return None
        _dispatchers[platform] = Dispatcher(make_context(client))
    return _dispatchers[platform]


@app.post("/webhook/{platform}/{secret}", include_in_schema=False)
async def webhook(platform: str, secret: str, request: Request):
    """Optional webhook receiver. The `secret` path segment must equal SECRET_KEY.

    Enabled only when a bot is configured for webhook mode; polling needs none of
    this. Telegram's `X-Telegram-Bot-Api-Secret-Token` header is also accepted.
    """
    settings = get_settings()
    header_secret = request.headers.get("x-telegram-bot-api-secret-token")
    if secret != settings.secret_key and header_secret != settings.secret_key:
        return JSONResponse(status_code=403, content={"detail": "forbidden"})
    resolved = _PLATFORMS.get(platform.lower())
    if resolved is None:
        return JSONResponse(status_code=404, content={"detail": "unknown platform"})
    dispatcher = _get_dispatcher(resolved)
    if dispatcher is None:
        return JSONResponse(status_code=503, content={"detail": "platform not configured"})
    update = await request.json()
    # Handler does blocking Bot API I/O — run off the event loop.
    await run_in_threadpool(dispatcher.handle_update, update)
    return {"ok": True}
