"""Test configuration.

Environment is set BEFORE importing the app so settings/engine pick up a
throwaway SQLite database, a temp upload dir, and fixed owner IDs. All network
(Telegram/Bale) is disabled so tests never send real messages.
"""

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="gymcore-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP.as_posix()}/test.db"
os.environ["UPLOAD_DIR"] = (_TMP / "uploads").as_posix()
os.environ["TELEGRAM_OWNER_IDS"] = "111,222"
os.environ["BALE_OWNER_IDS"] = "333"
os.environ["TELEGRAM_BOT_TOKEN"] = ""
os.environ["BALE_BOT_TOKEN"] = ""

import pytest  # noqa: E402

import app.models  # noqa: E402,F401 — register tables on Base.metadata
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.services import bootstrap  # noqa: E402
from app.services import notifications  # noqa: E402

# Keep every test fully offline.
notifications.enabled = False


@pytest.fixture()
def db():
    """A fresh, seeded database session per test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    bootstrap.seed_all(session)
    # There are no default class types anymore; tests that need one use this.
    from app.services import classes as classes_service

    classes_service.create(session, title="کلاس نمونه", key="sample")
    try:
        yield session
    finally:
        session.close()
