"""Reminder worker: `python -m app.jobs.reminders`.

Periodically scans active courses and sends due reminders through the shared
notification layer. Runs as its own process (Docker service / systemd unit),
mirroring how the Telegram and Bale bots run.
"""

from __future__ import annotations

import logging
import time

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.init import init_dev_schema
from app.db.session import session_scope
from app.services import reminders as reminders_service

logger = logging.getLogger(__name__)

_ERROR_BACKOFF_SECONDS = 30


def run_worker() -> None:
    setup_logging()
    settings = get_settings()
    if not settings.reminders_enabled:
        raise SystemExit("Reminders are disabled — set REMINDERS_ENABLED=true to run")

    init_dev_schema()
    interval = settings.reminder_interval_seconds
    logger.info("Reminder worker started (interval=%ss)", interval)

    while True:
        try:
            with session_scope() as db:
                sent = reminders_service.scan_and_send(db)
            logger.info("Reminder scan complete — %d sent", len(sent))
            time.sleep(interval)
        except Exception:
            logger.exception("Reminder scan failed — retrying shortly")
            time.sleep(_ERROR_BACKOFF_SECONDS)


if __name__ == "__main__":
    run_worker()
