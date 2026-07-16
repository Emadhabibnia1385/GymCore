"""Test fixtures.

Environment is configured BEFORE any app import so that the cached
Settings and the engine pick up the test database (SQLite file).
"""

import os
import tempfile

_TMP_DIR = tempfile.mkdtemp(prefix="gymcore-test-")
os.environ.update(
    {
        "DATABASE_URL": f"sqlite:///{_TMP_DIR}/test.db",
        "SECRET_KEY": "test-secret-key-0123456789abcdef0123456789abcdef",
        "UPLOAD_DIR": f"{_TMP_DIR}/uploads",
        "ADMIN_NAME": "مدیر تست",
        "ADMIN_PHONE": "09120000000",
        "ADMIN_PASSWORD": "admin-pass-123",
        "TELEGRAM_BOT_TOKEN": "",
        "BALE_BOT_TOKEN": "",
    }
)

import pytest
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.services import notifications

# Keep the whole suite offline.
notifications.enabled = False


@pytest.fixture(scope="session")
def client():
    # Context manager runs the lifespan: create_all + seed + bootstrap admin.
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def db(client):
    # Depends on `client` so the lifespan (create_all/seed) has already run.
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def admin_headers(client) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"phone": "09120000000", "password": "admin-pass-123"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    # Login also sets an auth cookie on the shared TestClient — drop it so
    # only explicit Authorization headers grant access in tests.
    client.cookies.clear()
    return {"Authorization": f"Bearer {token}"}


_phone_counter = iter(range(1000, 9999))


@pytest.fixture()
def unique_phone() -> str:
    """A fresh valid phone number per use (shared DB across the session)."""
    return f"0912100{next(_phone_counter)}"
