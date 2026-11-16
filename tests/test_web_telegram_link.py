"""«Connect Telegram»: a password account joins a Telegram account, approved in the bot."""

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.bots.common import web_login as bot_login
from app.core import clock
from app.core.config import get_settings
from app.models import Person, Platform, WebCredential, WebSession
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import identities as identities_service
from app.services import web_accounts
from tests.fakes import (
    callback_update,
    last_text,
    make_dispatcher,
    message_update,
    register,
)

OWNER = 111


@pytest.fixture()
def browser(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "web_cookie_secure", False)
    web_accounts.signups.reset()
    web_accounts.bot_logins.reset()
    return TestClient(app, headers={"user-agent": "Mozilla/5.0 Chrome/120 (Macintosh)"})


def _sign_up(browser, username="sara"):
    res = browser.post("/api/auth/register", json={
        "name": "سارا", "username": username, "password": "a-long-password-1"})
    assert res.status_code == 200, res.text


def _ask(browser):
    started = browser.post("/api/auth/telegram-link").json()
    return started["url"].rsplit("wk_", 1)[1]


def _telegram(user=5001, chat=700):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    register(disp, chat, user)
    return disp, client, chat, user


def _course(db, person_id):
    kind = classes_service.list_class_types(db, only_active=True)[0]
    courses_service.create(
        db, client_id=person_id, class_type_id=kind.id, sessions_total=12, tuition=1_000_000,
        start_date=clock.today(), weekdays="0", class_times="0@18:00",
    )


def test_the_button_needs_a_password_account_and_an_unlinked_telegram(db, browser):
    assert browser.post("/api/auth/telegram-link").status_code == 401
    _sign_up(browser)
    assert browser.get("/api/auth/telegram-link").json() == {"linked": False}
    started = browser.post("/api/auth/telegram-link").json()
    assert started["url"].startswith("https://t.me/MahdiSarmad_BOT?start=wk_")
    assert started["expires_in"] == 300


def test_a_fresh_web_account_gives_its_password_to_the_telegram_person(db, browser):
    _sign_up(browser)
    token = _ask(browser)
    disp, client, chat, user = _telegram()
    disp.handle_update(message_update(1, chat, user, f"/start wk_{token}"))
    assert "«sara»" in last_text(client)  # the bot names the account being joined
    disp.handle_update(callback_update(2, chat, user, f"wl:lok:{token}"))
    assert last_text(client) == bot_login.LINKED

    db.expire_all()
    person = identities_service.find_person(db, Platform.TELEGRAM, str(user))
    assert db.query(WebCredential).one().person_id == person.id
    assert db.query(Person).filter(Person.name == "سارا").count() == 0  # the web one is gone
    # The browser that asked is still signed in, now as that person, and sees it linked.
    assert browser.get("/api/auth/me").status_code == 200
    assert browser.get("/api/auth/telegram-link").json() == {"linked": True}
    assert db.query(WebSession).one().person_id == person.id
    # Password sign-in keeps working.
    other = TestClient(app)
    assert other.post("/api/auth/password", json={
        "username": "sara", "password": "a-long-password-1"}).status_code == 200


def test_a_web_account_with_a_course_keeps_its_story_and_takes_the_telegram_id(db, browser):
    _sign_up(browser)
    web = db.query(WebCredential).one().person_id
    _course(db, web)
    token = _ask(browser)
    disp, client, chat, user = _telegram()
    newcomer_id = identities_service.find_person(db, Platform.TELEGRAM, str(user)).id
    disp.handle_update(message_update(1, chat, user, f"/start wk_{token}"))
    disp.handle_update(callback_update(2, chat, user, f"wl:lok:{token}"))
    assert last_text(client) == bot_login.LINKED
    assert identities_service.find_person(db, Platform.TELEGRAM, str(user)).id == web
    db.expire_all()
    assert db.get(Person, newcomer_id) is None  # the empty one is gone


def test_two_accounts_with_histories_are_not_merged(db, browser):
    _sign_up(browser)
    _course(db, db.query(WebCredential).one().person_id)
    token = _ask(browser)
    disp, client, chat, user = _telegram()
    _course(db, identities_service.find_person(db, Platform.TELEGRAM, str(user)).id)
    disp.handle_update(message_update(1, chat, user, f"/start wk_{token}"))
    disp.handle_update(callback_update(2, chat, user, f"wl:lok:{token}"))
    assert last_text(client) == bot_login.LINK_PROBLEM["both"]
    assert browser.get("/api/auth/telegram-link").json() == {"linked": False}


def test_refusing_connects_nothing_and_a_link_is_one_answer(db, browser):
    _sign_up(browser)
    token = _ask(browser)
    disp, client, chat, user = _telegram()
    disp.handle_update(message_update(1, chat, user, f"/start wk_{token}"))
    disp.handle_update(callback_update(2, chat, user, f"wl:lno:{token}"))
    assert last_text(client) == bot_login.LINK_REFUSED
    disp.handle_update(callback_update(3, chat, user, f"wl:lok:{token}"))
    assert last_text(client) == bot_login.EXPIRED
    assert browser.get("/api/auth/telegram-link").json() == {"linked": False}


def test_the_coach_cannot_be_joined_to_a_password_account(db, browser):
    _sign_up(browser)
    token = _ask(browser)
    disp, client = make_dispatcher(Platform.TELEGRAM)
    disp.handle_update(message_update(1, 900, OWNER, f"/start wk_{token}"))
    disp.handle_update(callback_update(2, 900, OWNER, f"wl:lok:{token}"))
    assert last_text(client) == bot_login.LINK_PROBLEM["staff"]


def test_a_link_cannot_be_used_as_a_login_and_a_login_is_not_a_link(db, browser):
    _sign_up(browser)
    token = _ask(browser)
    from app.services import web_login
    person = db.query(Person).first()
    assert web_login.approve(db, token, person, "5001") is False  # not a sign-in request
    login = TestClient(app).post("/api/auth/bot-login").json()
    assert web_login.pending_link(db, login["url"].rsplit("wl_", 1)[1]) is None


def test_the_button_is_refused_once_telegram_is_there(db, browser):
    _sign_up(browser)
    token = _ask(browser)
    disp, client, chat, user = _telegram()
    disp.handle_update(message_update(1, chat, user, f"/start wk_{token}"))
    disp.handle_update(callback_update(2, chat, user, f"wl:lok:{token}"))
    assert browser.post("/api/auth/telegram-link").status_code == 409
