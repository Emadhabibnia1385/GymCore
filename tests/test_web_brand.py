"""The panel's name, title and logos."""
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


@pytest.fixture()
def coach(db, monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "web_cookie_secure", False)
    monkeypatch.setattr(get_settings(), "upload_dir", tmp_path)
    api = TestClient(app)
    person = identities_service.get_or_create_person(db, Platform.TELEGRAM, "111", "مربی")
    auth_service.sync_owner_role(db, Platform.TELEGRAM, "111", person)
    api.cookies.set("gc_session", web_auth.start_session(db, person, "111"))
    return api


def _png(width=300, height=100, color=(178, 248, 40, 255), fmt="PNG"):
    buffer = io.BytesIO()
    Image.new("RGBA" if fmt == "PNG" else "RGB", (width, height), color[: 4 if fmt == "PNG" else 3]).save(buffer, fmt)
    return buffer.getvalue()


def _upload(api, kind, content, name="logo.png"):
    return api.post(f"/api/admin/brand/logo/{kind}", files={"file": (name, content, "application/octet-stream")})


def test_the_defaults_are_english(db, coach):
    brand = TestClient(app).get("/api/brand").json()  # public: no sign-in
    assert (brand["name"], brand["title"]) == ("GymCore", "GymCore")
    assert brand["wide"] is False and brand["icon"] is False


def test_only_the_coach_can_change_the_brand(db, monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "web_cookie_secure", False)
    monkeypatch.setattr(get_settings(), "upload_dir", tmp_path)
    student = persons_service.create(db, name="سارا")
    identities_service.link_identity(db, student.id, Platform.TELEGRAM, "5001")
    api = TestClient(app)
    assert api.put("/api/admin/brand", json={"name": "x"}).status_code == 401
    api.cookies.set("gc_session", web_auth.start_session(db, student, "5001"))
    assert api.put("/api/admin/brand", json={"name": "x"}).status_code == 403
    assert _upload(api, "wide", _png()).status_code == 403
    assert api.delete("/api/admin/brand/logo/wide").status_code == 403


def test_the_name_and_title_are_set_and_validated(db, coach):
    ok = coach.put("/api/admin/brand", json={"name": "  Sarmad   Gym ", "title": "Sarmad Gym — پنل"})
    assert ok.json()["name"] == "Sarmad Gym" and ok.json()["title"] == "Sarmad Gym — پنل"
    assert coach.put("/api/admin/brand", json={"name": "Sarmad", "title": ""}).json()["title"] == "Sarmad"
    assert coach.put("/api/admin/brand", json={"name": "  ", "title": "x"}).status_code == 422
    assert coach.put("/api/admin/brand", json={"name": "x" * 61}).status_code == 422
    assert TestClient(app).get("/api/brand").json()["name"] == "Sarmad"


def test_a_wide_logo_is_stored_resized_and_served_to_everyone(db, coach):
    res = _upload(coach, "wide", _png(2000, 400))
    assert res.status_code == 200 and res.json()["wide"] is True and res.json()["version"] == 1
    served = TestClient(app).get("/api/brand/logo/wide")
    assert served.status_code == 200 and served.headers["content-type"] == "image/png"
    assert Image.open(io.BytesIO(served.content)).size == (800, 160)  # fitted, never cropped
    assert TestClient(app).get("/api/brand/logo/icon").status_code == 404  # no such kind


def test_an_icon_becomes_every_size_the_install_needs(db, coach):
    assert _upload(coach, "icon", _png(900, 300)).status_code == 200
    anon = TestClient(app)
    for size, side in (("512", 512), ("192", 192), ("180", 180), ("maskable", 512)):
        image = Image.open(io.BytesIO(anon.get(f"/api/brand/icon/{size}").content))
        assert image.size == (side, side)
    maskable = Image.open(io.BytesIO(anon.get("/api/brand/icon/maskable").content))
    assert maskable.getpixel((0, 0))[3] == 255  # opaque corners: safe inside any mask
    assert anon.get("/api/brand/icon/999").status_code == 404


def test_the_manifest_follows_the_brand(db, coach):
    anon = TestClient(app)
    first = anon.get("/api/brand/manifest.webmanifest").json()
    assert first["name"] == "GymCore" and first["icons"][0]["src"] == "/icons/icon-192.png"
    coach.put("/api/admin/brand", json={"name": "Sarmad", "title": "Sarmad Gym"})
    _upload(coach, "icon", _png(600, 600))
    again = anon.get("/api/brand/manifest.webmanifest")
    assert again.headers["content-type"].startswith("application/manifest+json")
    body = again.json()
    assert (body["name"], body["short_name"]) == ("Sarmad Gym", "Sarmad")
    assert [i["src"] for i in body["icons"]][0].startswith("/api/brand/icon/192?v=")
    assert any(i.get("purpose") == "maskable" for i in body["icons"])


def test_a_logo_can_be_removed_and_the_version_moves_on(db, coach):
    _upload(coach, "wide", _png())
    gone = coach.delete("/api/admin/brand/logo/wide").json()
    assert gone["wide"] is False and gone["version"] == 2
    assert TestClient(app).get("/api/brand/logo/wide").status_code == 404
    assert coach.delete("/api/admin/brand/logo/nope").status_code == 422


def test_a_file_that_is_not_a_safe_image_is_refused(db, coach):
    assert _upload(coach, "wide", b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", "x.svg").status_code == 422
    assert _upload(coach, "wide", b"not an image at all").status_code == 422
    assert _upload(coach, "wide", b"\x89PNG\r\n\x1a\n" + b"\x00" * 50).status_code == 422  # a header and nothing else
    gif = io.BytesIO()
    Image.new("P", (10, 10)).save(gif, "GIF")
    assert _upload(coach, "wide", gif.getvalue(), "x.gif").status_code == 422  # not an allowed format
    assert _upload(coach, "wide", _png(5000, 10)).status_code == 422  # too large a side
    assert _upload(coach, "wide", b"\x00" * (5 * 1024 * 1024 + 10)).status_code == 422
    assert _upload(coach, "banana", _png()).status_code == 422
    assert TestClient(app).get("/api/brand").json()["wide"] is False  # nothing was stored


def test_a_jpeg_is_accepted_and_stored_as_png(db, coach):
    assert _upload(coach, "wide", _png(400, 120, fmt="JPEG"), "photo.jpg").status_code == 200
    served = TestClient(app).get("/api/brand/logo/wide")
    assert served.content.startswith(b"\x89PNG")
