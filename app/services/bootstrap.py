"""Startup seeding — idempotent defaults for settings and catalogs.

Called once by every entrypoint (API lifespan, bot runners). On SQLite (dev)
the schema comes from create_all and these seeds populate it; on Postgres the
schema and initial catalog rows come from Alembic, and these calls are no-ops
because the rows already exist.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.services import classes as classes_service
from app.services import contact_links as contact_links_service
from app.services import plans as plans_service
from app.services import settings as settings_service


def seed_all(db: Session) -> None:
    settings_service.seed_defaults(db)
    classes_service.seed_defaults(db)
    plans_service.seed_defaults(db)
    contact_links_service.seed_defaults(db)
