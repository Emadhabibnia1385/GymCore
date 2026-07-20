"""Hardening: malformed callbacks never crash, and the client contact flow
creates no ordering side-effects (this is a management system, not a pipeline)."""

from sqlalchemy import func, select

from app.bots.common import callbacks as cb
from app.copy import texts
from app.models import Course, Notification, Payment, PlanAssignment
from tests.fakes import button_texts, callback_update, last_markup, make_dispatcher, register


def test_parse_int_rejects_tampered_values():
    assert cb.parse_int("5") == 5
    assert cb.parse_int("abc") is None
    assert cb.parse_int("-5") is None
    assert cb.parse_int(None) is None
    assert cb.parse_int("") is None


def test_garbage_callback_falls_back_to_menu(db):
    disp, client = make_dispatcher()
    register(disp, 500, 700)
    disp.handle_update(callback_update(1, 500, 700, "💥garbage💥"))
    assert texts.BTN_REGISTER_CLASS in button_texts(last_markup(client))


def test_empty_callback_does_not_crash(db):
    disp, client = make_dispatcher()
    register(disp, 500, 700)
    disp.handle_update(callback_update(1, 500, 700, ""))
    assert texts.BTN_REGISTER_CLASS in button_texts(last_markup(client))


def test_admin_unknown_section_returns_to_panel(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, 500, 111, "a:zzzz:1"))  # owner, bad section
    assert any(texts.ADMIN_TITLE in (s.get("text") or "") for s in client.sent)


def test_admin_malformed_id_is_ignored(db):
    disp, client = make_dispatcher()
    # Non-numeric course id must not raise (rest.isdigit() guards it).
    disp.handle_update(callback_update(1, 500, 111, "a:courses:view:notanumber"))
    assert client.sent  # produced a response, did not crash


def test_register_contact_creates_no_records(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, 500, 700, cb.REGISTER))
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Course)) == 0
    assert db.scalar(select(func.count()).select_from(Payment)) == 0
    assert db.scalar(select(func.count()).select_from(PlanAssignment)) == 0
    assert db.scalar(select(func.count()).select_from(Notification)) == 0
