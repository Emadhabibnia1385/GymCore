"""«Log in with the bot»: the browser asks, the person approves inside Telegram."""

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.bots.common import web_login as bot_login
from app.core.config import get_settings
from app.models import Platform
from app.services import identities as identities_service
from app.services import persons as persons_service
from app.services import web_accounts
from tests.fakes import (
    button_texts,
    callback_update,
    last_markup,
    last_text,
    make_dispatcher,
    message_update,
    register,
)

CHROME_MAC = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
)
OWNER = 111


@pytest.fixture()
def browser(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "web_cookie_secure", False)
    web_accounts.bot_logins.reset()
    api = TestClient(app, headers={"user-agent": CHROME_MAC})
    return api


def _ask(browser):
    started = browser.post("/api/auth/bot-login").json()
    token = started["url"].rsplit("wl_", 1)[1]
    return started["secret"], token


def _poll(browser, secret):
    return browser.post("/api/auth/bot-login/status", json={"secret": secret}).json()


def _student_chat(db, user_id=5001, chat=700):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    register(disp, chat, user_id)
    return disp, client, chat, user_id


def test_the_panel_hands_out_a_bot_link(db, browser):
    started = browser.post("/api/auth/bot-login").json()
    assert started["url"].startswith("https://t.me/MahdiSarmad_BOT?start=wl_")
    assert started["expires_in"] == 300
    assert _poll(browser, started["secret"]) == {"state": "pending", "me": None}


def test_a_student_confirms_in_the_bot_and_the_browser_is_signed_in_once(db, browser):
    secret, token = _ask(browser)
    disp, client, chat, user = _student_chat(db)
    disp.handle_update(message_update(1, chat, user, f"/start wl_{token}"))
    text = last_text(client)
    assert "Chrome روی Mac" in text and "درخواست ورود" in text  # who is asking
    assert button_texts(last_markup(client)) == [bot_login.CONFIRM, bot_login.REFUSE]
    disp.handle_update(callback_update(2, chat, user, f"wl:ok:{token}"))
    assert last_text(client) == bot_login.DONE

    done = _poll(browser, secret)
    assert done["state"] == "approved" and done["me"]["role"] == "student"
    assert browser.get("/api/auth/me").status_code == 200  # the cookie was set
    assert _poll(browser, secret)["state"] == "expired"  # the session can't be taken twice


def test_the_coach_signs_in_as_admin_through_the_bot(db, browser):
    secret, token = _ask(browser)
    disp, client = make_dispatcher(Platform.TELEGRAM)
    disp.handle_update(message_update(1, 900, OWNER, f"/start wl_{token}"))
    disp.handle_update(callback_update(2, 900, OWNER, f"wl:ok:{token}"))
    assert _poll(browser, secret)["me"]["role"] == "admin"
    assert browser.get("/api/admin/students").status_code == 200


def test_refusing_signs_nobody_in(db, browser):
    secret, token = _ask(browser)
    disp, client, chat, user = _student_chat(db)
    disp.handle_update(message_update(1, chat, user, f"/start wl_{token}"))
    disp.handle_update(callback_update(2, chat, user, f"wl:no:{token}"))
    assert last_text(client) == bot_login.REFUSED
    assert _poll(browser, secret)["state"] == "denied"
    assert browser.get("/api/auth/me").status_code == 401
    # Approving after refusing does nothing.
    disp.handle_update(callback_update(3, chat, user, f"wl:ok:{token}"))
    assert last_text(client) == bot_login.EXPIRED


def test_a_link_nobody_opened_a_bad_secret_and_tampered_buttons_get_nothing(db, browser):
    assert _poll(browser, "made-up-secret")["state"] == "expired"
    disp, client, chat, user = _student_chat(db)
    disp.handle_update(message_update(1, chat, user, "/start wl_AAAAAAAAAAAAAAAAAAAAAAAA"))
    assert last_text(client) == bot_login.EXPIRED  # a well-formed token nobody issued
    disp.handle_update(message_update(2, chat, user, "/start wl_bad"))
    assert last_text(client) == bot_login.EXPIRED  # malformed
    for tampered in ("wl:ok", "wl:ok:", "wl:zz:AAAAAAAAAAAAAAAAAAAAAAAA", "wl:ok:../../x"):
        disp.handle_update(callback_update(3, chat, user, tampered))
        assert last_text(client) == bot_login.EXPIRED


def test_an_expired_request_cannot_be_approved(db, browser):
    from datetime import UTC, datetime, timedelta

    from app.models import WebLoginRequest

    secret, token = _ask(browser)
    row = db.query(WebLoginRequest).one()
    row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()
    disp, client, chat, user = _student_chat(db)
    disp.handle_update(message_update(1, chat, user, f"/start wl_{token}"))
    assert last_text(client) == bot_login.EXPIRED
    assert _poll(browser, secret)["state"] == "expired"


def test_bale_is_told_this_is_telegram_only(db, browser):
    _, token = _ask(browser)
    disp, client = make_dispatcher(Platform.BALE)
    register(disp, 700, 5001)
    disp.handle_update(message_update(1, 700, 5001, f"/start wl_{token}"))
    assert last_text(client) == bot_login.TELEGRAM_ONLY


def test_a_deactivated_person_cannot_approve(db, browser):
    secret, token = _ask(browser)
    disp, client, chat, user = _student_chat(db)
    person = identities_service.find_person(db, Platform.TELEGRAM, str(user))
    persons_service.update(db, person.id, is_active=False)
    disp.handle_update(message_update(1, chat, user, f"/start wl_{token}"))
    disp.handle_update(callback_update(2, chat, user, f"wl:ok:{token}"))
    assert _poll(browser, secret)["state"] == "pending"


def test_starting_requests_is_throttled_per_client(db, browser):
    for _ in range(10):
        assert browser.post("/api/auth/bot-login").status_code == 200
    assert browser.post("/api/auth/bot-login").status_code == 429
