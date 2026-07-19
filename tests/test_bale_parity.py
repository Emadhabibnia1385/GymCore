"""Bale parity: the SAME shared handlers must work on Bale, with Bale-specific
interaction adaptations (fresh messages instead of edits, URL instead of Web App,
per-platform owner IDs)."""

from sqlalchemy import select

from app.bots.common import callbacks as cb
from app.copy import texts
from app.models import Person, Platform, Role
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import persons as persons_service
from tests.fakes import (
    button_urls,
    callback_update,
    last_markup,
    make_dispatcher,
    message_update,
    web_app_urls,
)

BALE_OWNER = 333  # configured in conftest (BALE_OWNER_IDS=333)
CHAT = 800


def test_bale_navigation_sends_fresh_messages_not_edits(db):
    """Bale editing of keyboard messages is unreliable → always send fresh."""
    disp, client = make_dispatcher(Platform.BALE)
    disp.handle_update(message_update(1, CHAT, 700, "/start"))
    client.sent.clear()
    disp.handle_update(callback_update(2, CHAT, 700, cb.CONTACT))
    assert client.sent[-1]["method"] == "send_message"
    assert all(s["method"] != "edit_message_text" for s in client.sent)


def test_bale_order_uses_url_button_not_webapp(db):
    disp, client = make_dispatcher(Platform.BALE)
    disp.handle_update(callback_update(1, CHAT, 700, cb.ORDER))
    markup = last_markup(client)
    assert not web_app_urls(markup)
    assert any("signup" in url for url in button_urls(markup))


def test_bale_admin_create_student_parity(db):
    disp, client = make_dispatcher(Platform.BALE)
    disp.handle_update(callback_update(1, CHAT, BALE_OWNER, cb.ADMIN))
    disp.handle_update(callback_update(2, CHAT, BALE_OWNER, "a:students:new"))
    disp.handle_update(message_update(3, CHAT, BALE_OWNER, "شاگرد بله"))
    disp.handle_update(callback_update(4, CHAT, BALE_OWNER, "a:students:new_phone_skip"))
    db.expire_all()
    assert db.scalar(select(Person).where(Person.name == "شاگرد بله")) is not None


def test_bale_admin_attendance_parity(db):
    disp, client = make_dispatcher(Platform.BALE)
    student = persons_service.create(db, name="شاگرد بله ۲", role=Role.CLIENT)
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=student.id, class_type_id=class_type.id, sessions_total=5
    )
    disp.handle_update(callback_update(1, CHAT, BALE_OWNER, f"a:attend:course:{course.id}"))
    disp.handle_update(message_update(2, CHAT, BALE_OWNER, "1405/05/01"))
    disp.handle_update(callback_update(3, CHAT, BALE_OWNER, "a:attend:outcome:PRESENT"))
    disp.handle_update(callback_update(4, CHAT, BALE_OWNER, "a:attend:note_skip"))
    db.expire_all()
    assert courses_service.consumed_sessions(db, course.id) == 1


def test_bale_owner_scope_is_per_platform(db):
    # 333 is the Bale owner; 111 (the Telegram owner) is NOT an admin on Bale.
    disp, client = make_dispatcher(Platform.BALE)
    disp.handle_update(callback_update(1, CHAT, 111, "a:students"))
    assert client.answered[-1]["show_alert"] is True
    assert not any(texts.ADMIN_TITLE in (s.get("text") or "") for s in client.sent)

    disp.handle_update(callback_update(2, CHAT, BALE_OWNER, cb.ADMIN))
    assert any(texts.ADMIN_TITLE in (s.get("text") or "") for s in client.sent)
