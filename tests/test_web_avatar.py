"""Profile photos: a person changes their own, the coach sets a student's."""
# ruff: noqa: E501  (request bodies read best on one line)

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.main import app
from app.core.config import get_settings
from app.models import Platform
from app.services import auth as auth_service
from app.services import identities as identities_service
from app.services import persons as persons_service
from app.services import web_auth


@pytest.fixture(autouse=True)
def _env(monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "web_cookie_secure", False)
    monkeypatch.setattr(get_settings(), "upload_dir", tmp_path)


def _signed_in(db, person, telegram_id=None):
    api = TestClient(app)
    api.cookies.set("gc_session", web_auth.start_session(db, person, telegram_id))
    return api


@pytest.fixture()
def coach(db):
    person = identities_service.get_or_create_person(db, Platform.TELEGRAM, "111", "مربی")
    auth_service.sync_owner_role(db, Platform.TELEGRAM, "111", person)
    return _signed_in(db, person, "111")


def _photo(width=640, height=320, fmt="PNG"):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (178, 248, 40)).save(buffer, fmt)
    return buffer.getvalue()


def _send(api, url, content, name="me.png"):
    return api.post(url, files={"file": (name, content, "application/octet-stream")})


def test_a_student_sets_and_removes_their_own_photo(db):
    student = persons_service.create(db, name="سارا")
    api = _signed_in(db, student)
    assert api.get("/api/me/avatar").status_code == 404
    assert api.get("/api/auth/me").json()["avatar"] is None

    assert _send(api, "/api/me/avatar", _photo()).json() == {"version": 1}
    assert api.get("/api/auth/me").json()["avatar"] == 1
    shown = api.get("/api/me/avatar")
    assert shown.status_code == 200 and shown.headers["content-type"] == "image/png"
    assert "private" in shown.headers["cache-control"]
    assert Image.open(io.BytesIO(shown.content)).size == (256, 256)  # cropped square, shrunk

    assert _send(api, "/api/me/avatar", _photo(300, 500, "JPEG")).json() == {"version": 2}
    assert api.delete("/api/me/avatar").json() == {"version": 0}
    assert api.get("/api/me/avatar").status_code == 404


def test_a_bad_file_is_refused(db):
    api = _signed_in(db, persons_service.create(db, name="سارا"))
    assert _send(api, "/api/me/avatar", b"not an image").status_code == 422
    assert _send(api, "/api/me/avatar", b"<svg xmlns='http://www.w3.org/2000/svg'/>", "a.svg").status_code == 422
    assert _send(api, "/api/me/avatar", _photo(5000, 10)).status_code == 422  # too large a side
    assert api.get("/api/me/avatar").status_code == 404


def test_the_coach_sets_a_students_photo_and_a_student_cannot(db, coach):
    student = persons_service.create(db, name="سارا")
    other = persons_service.create(db, name="علی")
    assert _send(coach, f"/api/admin/students/{student.id}/avatar", _photo()).json() == {"version": 1}
    assert coach.get(f"/api/admin/students/{student.id}/avatar").status_code == 200
    assert coach.get(f"/api/admin/students/{student.id}").json()["avatar"] == 1
    assert [r["avatar"] for r in coach.get("/api/admin/students").json()["rows"]] == [1, 0]

    mine = _signed_in(db, other)
    assert _send(mine, f"/api/admin/students/{student.id}/avatar", _photo()).status_code == 403
    assert mine.get(f"/api/admin/students/{student.id}/avatar").status_code == 403  # nor read another's
    assert coach.delete(f"/api/admin/students/{student.id}/avatar").json() == {"version": 0}
    assert coach.get("/api/admin/students/99999/avatar").status_code == 404


def test_the_photo_needs_a_signed_in_person(db):
    assert TestClient(app).get("/api/me/avatar").status_code == 401
    assert _send(TestClient(app), "/api/me/avatar", _photo()).status_code == 401
