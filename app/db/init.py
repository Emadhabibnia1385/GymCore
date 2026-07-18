"""Schema initialization shared by every entrypoint (API, bots, worker).

Local SQLite (dev/test) has its tables created directly from the models — fast
and migration-free. Postgres (production) is owned by Alembic: run
`alembic upgrade head` on deploy. This keeps a single, explicit rule for where
the schema comes from, instead of `create_all` racing migrations on Postgres.
"""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine

logger = logging.getLogger(__name__)


def init_dev_schema() -> None:
    """Create tables for SQLite; no-op (migration-managed) for other engines."""
    import app.models  # noqa: F401 — register every table on Base.metadata

    if get_settings().is_sqlite:
        Base.metadata.create_all(bind=engine)
    else:
        logger.info("Non-SQLite database detected — schema is managed by Alembic")
