"""Username/password sign-in and sign-up for the web panel."""
# ruff: noqa: E501  (request bodies read best on one line)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.main import app
from app.core.config import get_settings
from app.models import Person, Platform, Role, WebCredential, WebSession
from app.models.setting import KEY_WEB_REGISTRATION
from app.services import auth as auth_service
from app.services import crm as crm_service
from app.services import identities as identities_service
from app.services import persons as persons_service
from app.services import settings as settings_service
from app.services import web_accounts, web_auth


@pytest.fixture()
def api(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "web_cookie_secure", False)  # the test client is http
    web_accounts.failed_logins.reset()
    web_accounts.signups.reset()
    return TestClient(app)


def _register(api, name="سارا", username="sara", password="correct-horse"):
    return api.post("/api/auth/register", json={"name": name, "username": username, "password": password})


def test_a_student_signs_up_and_is_signed_in_at_once(db, api):
    res = _register(api)
    assert res.status_code == 200
    assert res.json() == {"name": "سارا", "role": "student", "username": "sara", "avatar": None}
    assert api.get("/api/auth/me").json()["username"] == "sara"
    person = db.scalar(select(Person).where(Person.name == "سارا"))
    assert person.phone is None  # an unverified phone would be a way to claim someone's account
    assert db.scalar(select(WebSession)).telegram_user_id is None
    # The coach finds the newcomer among today's follow-ups.
    assert [f.person_id for f in crm_service.list_due(db)] == [person.id]


def test_the_password_is_stored_only_as_an_argon2_hash(db, api):
    _register(api, password="correct-horse")
    stored = db.scalar(select(WebCredential)).password_hash
    assert stored.startswith("$argon2id$") and "correct-horse" not in stored


def test_signing_in_with_a_password_works_and_remembers(db, api):
    _register(api)
    api.post("/api/auth/logout")
    res = api.post("/api/auth/password", json={"username": "Sara", "password": "correct-horse"})
    assert res.status_code == 200 and res.json()["username"] == "sara"  # case-insensitive name
    assert api.get("/api/auth/me").status_code == 200


def test_a_wrong_password_and_an_unknown_user_look_identical(db, api):
    _register(api)
    api.post("/api/auth/logout")
    wrong = api.post("/api/auth/password", json={"username": "sara", "password": "nope-nope"})
    unknown = api.post("/api/auth/password", json={"username": "ghost", "password": "nope-nope"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_too_many_failures_are_throttled_even_for_the_right_password(db, api):
    _register(api)
    api.post("/api/auth/logout")
    for _ in range(5):
        api.post("/api/auth/password", json={"username": "sara", "password": "wrong-wrong"})
    res = api.post("/api/auth/password", json={"username": "sara", "password": "correct-horse"})
    assert res.status_code == 429


def test_username_and_password_rules_and_duplicates(db, api):
    assert _register(api, username="ab").status_code == 422  # too short
    assert _register(api, username="has space").status_code == 422
    assert _register(api, password="short").status_code == 422
    assert _register(api, username="sara", password="sara").status_code == 422
    assert _register(api, username="sara").status_code == 200
    api.post("/api/auth/logout")
    assert _register(api, name="مریم", username="SARA").status_code == 409  # same name, any case


def test_registration_can_be_closed_by_the_coach(db, api):
    assert api.get("/api/auth/config").json()["registration_open"] is True
    settings_service.set_value(db, KEY_WEB_REGISTRATION, "0")
    assert api.get("/api/auth/config").json()["registration_open"] is False
    assert _register(api).status_code == 403


def test_sign_ups_are_throttled_per_client(db, api):
    for i in range(5):
        assert _register(api, username=f"user{i}x").status_code == 200
        api.post("/api/auth/logout")
    assert _register(api, username="sixth").status_code == 429


def test_a_student_can_change_their_own_password(db, api):
    _register(api)
    bad = api.post("/api/auth/password/change", json={"old_password": "wrong-wrong", "new_password": "a-new-secret"})
    assert bad.status_code == 403
    ok = api.post("/api/auth/password/change", json={"old_password": "correct-horse", "new_password": "a-new-secret"})
    assert ok.status_code == 200
    api.post("/api/auth/logout")
    assert api.post("/api/auth/password", json={"username": "sara", "password": "a-new-secret"}).status_code == 200


def test_a_password_session_is_never_an_admin_unless_the_person_is_the_coach(db, api):
    _register(api)
    assert api.get("/api/admin/students").status_code == 403
    # The coach, who is an owner, gives himself a login; the COACH role makes it admin.
    coach = identities_service.get_or_create_person(db, Platform.TELEGRAM, "111", "مربی")
    auth_service.sync_owner_role(db, Platform.TELEGRAM, "111", coach)
    assert coach.role == Role.COACH
    web_accounts.set_credentials(db, coach.id, "coach", "coach-password")
    api.post("/api/auth/logout")
    res = api.post("/api/auth/password", json={"username": "coach", "password": "coach-password"})
    assert res.json()["role"] == "admin"
    assert api.get("/api/admin/students").status_code == 200


def test_the_coach_gives_a_student_access_and_can_reset_it(db, api):
    student = persons_service.create(db, name="مریم")
    coach = identities_service.get_or_create_person(db, Platform.TELEGRAM, "111", "مربی")
    auth_service.sync_owner_role(db, Platform.TELEGRAM, "111", coach)
    api.cookies.set("gc_session", web_auth.start_session(db, coach, "111"))
    res = api.post(f"/api/admin/students/{student.id}/web-access", json={"username": "maryam", "password": "first-pass-1"})
    assert res.status_code == 200
    assert api.get(f"/api/admin/students/{student.id}").json()["username"] == "maryam"
    again = api.post(f"/api/admin/students/{student.id}/web-access", json={"username": "maryam", "password": "second-pass-2"})
    assert again.status_code == 200
    other = persons_service.create(db, name="رضا")
    clash = api.post(f"/api/admin/students/{other.id}/web-access", json={"username": "maryam", "password": "whatever-123"})
    assert clash.status_code == 409
    fresh = TestClient(app)
    assert fresh.post("/api/auth/password", json={"username": "maryam", "password": "second-pass-2"}).status_code == 200


def test_deleting_a_student_removes_their_login(db, api):
    _register(api)
    person = db.scalar(select(Person).where(Person.name == "سارا"))
    persons_service.delete(db, person.id)
    assert db.scalar(select(WebCredential)) is None


def test_a_telegram_user_can_add_their_own_login_once(db, api):
    student = persons_service.create(db, name="نگار")
    identities_service.link_identity(db, student.id, Platform.TELEGRAM, "5009")
    api.cookies.set("gc_session", web_auth.start_session(db, student, "5009"))
    ok = api.post("/api/auth/password/set", json={"username": "negar", "password": "my-own-pass1"})
    assert ok.status_code == 200 and ok.json()["username"] == "negar"
    assert api.post("/api/auth/password/set", json={"username": "negar2", "password": "my-own-pass1"}).status_code == 409
