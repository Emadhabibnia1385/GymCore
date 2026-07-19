"""Long-polling runner shared by both bot entrypoints.

Long polling is the safe default — the bots need no public web endpoint to
operate (see install.sh / README for optional webhook mode).
"""

from __future__ import annotations

import logging
import time

from app.bots.common.client import build_client
from app.bots.common.context import make_context
from app.bots.common.router import Dispatcher
from app.core.logging import setup_logging
from app.db.init import init_dev_schema
from app.db.session import session_scope
from app.models import Platform
from app.services import bootstrap

logger = logging.getLogger(__name__)

_ERROR_BACKOFF_SECONDS = 5


def run_bot(platform: Platform) -> None:
    setup_logging()
    client = build_client(platform)
    if client is None:
        raise SystemExit(f"{platform.value} bot token is not configured — set it in .env")

    # Idempotent: makes a standalone bot run (without the API process) safe too.
    init_dev_schema()
    with session_scope() as db:
        bootstrap.seed_all(db)

    ctx = make_context(client)
    dispatcher = Dispatcher(ctx)

    me = client.call("getMe")
    logger.info("%s bot started as @%s", platform.value, (me or {}).get("username"))

    # Register the /start command so it appears in the bot's command menu.
    try:
        client.set_my_commands([{"command": "start", "description": "شروع و منوی اصلی"}])
    except Exception:
        logger.debug("setMyCommands failed (non-fatal)")

    offset: int | None = None
    while True:
        try:
            updates = client.get_updates(offset=offset)
        except Exception:
            logger.exception("getUpdates failed — retrying")
            time.sleep(_ERROR_BACKOFF_SECONDS)
            continue
        for update in updates:
            offset = update["update_id"] + 1
            dispatcher.handle_update(update)
