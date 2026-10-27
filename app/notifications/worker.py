"""Background notification worker: generate reminders + dispatch due notifications.

Run as its own process:  `python -m app.notifications.worker`

Admin-triggered broadcasts and reminders are dispatched immediately by the bot
handlers; this worker is the periodic safety net that also produces the
automatic low-session / course-ending reminders, the coach's morning
«📇 پیگیری‌ها» digest (notifications/digest.py), and delivers anything scheduled.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.init import init_dev_schema
from app.db.session import session_scope
from app.notifications import digest, service
from app.services import bootstrap

logger = logging.getLogger(__name__)


def run_once(now: datetime | None = None) -> tuple[int, int]:
    """One worker cycle: (reminders queued, notifications delivered)."""
    settings = get_settings()
    queued = 0
    with session_scope() as db:
        if settings.reminders_enabled:
            queued = service.generate_reminders(db)
            queued += _queue_digest(db, now)
        delivered = service.dispatch_due(db, now=now)
    return queued, delivered


def _queue_digest(db, now: datetime | None) -> int:
    """The coach's digest must never hold up the students' reminders."""
    try:
        return digest.queue_digest(db, now=now)
    except Exception:
        logger.exception("crm digest failed")
        db.rollback()
        return 0


def run_worker() -> None:
    setup_logging()
    init_dev_schema()
    with session_scope() as db:
        bootstrap.seed_all(db)

    interval = max(get_settings().reminder_interval_seconds, 60)
    logger.info("notification worker started (interval=%ss)", interval)
    while True:
        try:
            queued, delivered = run_once()
            if queued or delivered:
                logger.info("worker cycle: %s reminder(s) queued, %s delivered", queued, delivered)
        except Exception:
            logger.exception("worker cycle failed")
        time.sleep(interval)


if __name__ == "__main__":
    run_worker()
