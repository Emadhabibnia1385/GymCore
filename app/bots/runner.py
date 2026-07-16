"""Long-polling runner shared by both bot entrypoints."""

from __future__ import annotations

import logging
import time

from app.bots.client import BotClient, build_client
from app.bots.handlers import BotHandler
from app.core.logging import setup_logging
from app.db.base import Base
from app.db.session import engine
from app.models import Platform

logger = logging.getLogger(__name__)

_ERROR_BACKOFF_SECONDS = 5


def run_bot(platform: Platform) -> None:
    setup_logging()
    client: BotClient | None = build_client(platform)
    if client is None:
        raise SystemExit(
            f"{platform.value} bot token is not configured — set it in .env"
        )

    # Idempotent: makes standalone bot runs (without the API) safe too.
    Base.metadata.create_all(bind=engine)

    me = client.call("getMe")
    logger.info("%s bot started as @%s", platform.value, me.get("username"))

    handler = BotHandler(client)
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
            handler.handle_update(update)
