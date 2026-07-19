"""Client bot flow: inline menus, register→contact, order→URL, courses,
programs, contact, and admin-button visibility / callback tamper rejection."""

from datetime import date

import app.models as models
from app.bots.common import callbacks as cb
from app.copy import texts
from app.models import AttendanceStatus, Platform
from app.models.setting import KEY_REGISTER_CONTACT_TEXT
from app.services import attendance as attendance_service
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import identities as identities_service
from app.services import plans as plans_service
from app.services import settings as settings_service
from tests.fakes import (
    button_texts,
    button_urls,
    callback_update,
    last_markup,
    last_text,
    make_dispatcher,
    message_update,
    web_app_urls,
)


def test_start_shows_client_menu_without_admin_button(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    disp.handle_update(message_update(1, 500, 700, "/start"))
    labels = button_texts(last_markup(client))
    assert texts.BTN_REGISTER_CLASS in labels
    assert texts.BTN_ORDER_PLAN in labels
    assert texts.BTN_MY_CLASSES in labels
    assert texts.BTN_MY_PLANS in labels
    assert texts.BTN_CONTACT in labels
    assert texts.BTN_ADMIN_PANEL not in labels  # normal client
    db.expire_all()
    assert identities_service.find_person(db, Platform.TELEGRAM, "700") is not None


def test_owner_sees_admin_button_and_is_promoted(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    disp.handle_update(message_update(1, 500, 111, "/start"))  # 111 is a configured owner
    assert texts.BTN_ADMIN_PANEL in button_texts(last_markup(client))
    db.expire_all()
    owner = identities_service.find_person(db, Platform.TELEGRAM, "111")
    assert owner.role.value == "COACH"


def test_no_request_models_exist():
    for name in ("ClassRequest", "PlanRequest", "ClassRegistrationRequest", "RequestStatus"):
        assert not hasattr(models, name)


def test_register_shows_contact_links_not_a_form(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    disp.handle_update(callback_update(1, 500, 700, cb.REGISTER))
    body = last_text(client)
    assert settings_service.get_value(db, KEY_REGISTER_CONTACT_TEXT) in body
    # No phone is ever requested, no contact-sharing, no request created.
    assert "شماره" not in body
    urls = button_urls(last_markup(client))
    assert any(u.startswith("https://t.me/") for u in urls)


def test_order_button_is_a_plain_url_link_on_both_platforms(db):
    for platform in (Platform.TELEGRAM, Platform.BALE):
        disp, client = make_dispatcher(platform)
        disp.handle_update(message_update(1, 500, 700, "/start"))
        markup = last_markup(client)
        assert not web_app_urls(markup)  # a plain link — never a Mini App
        assert any("mahdisarmad.ir/signup" in url for url in button_urls(markup))


def test_telegram_menu_buttons_carry_colour_styles(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    disp.handle_update(message_update(1, 500, 700, "/start"))
    styles = {
        b["text"]: b.get("style")
        for row in last_markup(client)["inline_keyboard"]
        for b in row
    }
    assert styles[texts.BTN_REGISTER_CLASS] == "primary"  # blue
    assert styles[texts.BTN_ORDER_PLAN] == "primary"
    assert styles[texts.BTN_MY_CLASSES] == "success"  # green
    assert styles[texts.BTN_MY_PLANS] == "success"
    assert styles[texts.BTN_CONTACT] == "danger"  # red


def test_bale_menu_buttons_have_no_style(db):
    # Bale doesn't support the style field — must not send it (would be rejected).
    disp, client = make_dispatcher(Platform.BALE)
    disp.handle_update(message_update(1, 500, 700, "/start"))
    for row in last_markup(client)["inline_keyboard"]:
        for button in row:
            assert "style" not in button


def test_my_courses_empty_state(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, 500, 700, cb.COURSES))
    assert last_text(client) == texts.NO_COURSES


def test_my_courses_list_and_detail_derive_remaining(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    disp.handle_update(message_update(1, 500, 700, "/start"))
    db.expire_all()
    person = identities_service.find_person(db, Platform.TELEGRAM, "700")
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=person.id, class_type_id=class_type.id,
        sessions_total=8, start_date=date(2026, 7, 1),
    )
    attendance_service.record(
        db, course.id, date(2026, 7, 1), AttendanceStatus.PRESENT, notify=False
    )

    client.sent.clear()
    disp.handle_update(callback_update(2, 500, 700, cb.COURSES))
    assert any("جلسه باقی‌مانده" in label for label in button_texts(last_markup(client)))

    client.sent.clear()
    disp.handle_update(callback_update(3, 500, 700, cb.course(course.id)))
    detail = last_text(client)
    assert texts.LABEL_REMAINING in detail
    assert "7" in detail  # 8 total − 1 consumed


def test_course_detail_rejects_other_clients_course(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    disp.handle_update(message_update(1, 500, 700, "/start"))
    db.expire_all()
    owner_person = identities_service.find_person(db, Platform.TELEGRAM, "700")
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=owner_person.id, class_type_id=class_type.id,
        sessions_total=5, start_date=date(2026, 7, 1),
    )
    # A different account cannot open person A's course.
    client.sent.clear()
    disp.handle_update(callback_update(2, 501, 800, cb.course(course.id)))
    assert last_text(client) == texts.NOT_FOUND


def test_programs_list_and_file_delivery(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    disp.handle_update(message_update(1, 500, 700, "/start"))
    db.expire_all()
    person = identities_service.find_person(db, Platform.TELEGRAM, "700")
    training = plans_service.get_type_by_key(db, "training")
    plans_service.create_assignment(
        db, person_id=person.id, plan_type_id=training.id, title="برنامه من",
        platform_file_id="FILEID", file_platform=Platform.TELEGRAM, notify=False,
    )
    assignment_id = plans_service.list_assignments(db, person_id=person.id)[0].id

    client.sent.clear()
    disp.handle_update(callback_update(2, 500, 700, cb.PROGRAMS))
    assert any("برنامه من" in label for label in button_texts(last_markup(client)))

    client.sent.clear()
    disp.handle_update(callback_update(3, 500, 700, cb.program(assignment_id)))
    methods = [s["method"] for s in client.sent]
    assert "send_document_id" in methods
    assert any(s.get("text") == texts.PROGRAM_SENT for s in client.sent)


def test_contact_us_renders_links_and_keeps_tel_mailto_as_text(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, 500, 700, cb.CONTACT))
    # Regression: mailto:/tel: must NOT become inline buttons (they crash the
    # message), so the message renders fine and they appear as text instead.
    assert last_text(client) != texts.ERROR
    urls = button_urls(last_markup(client))
    assert any("wa.me" in url for url in urls)  # https links became buttons
    assert all("mailto:" not in url and "tel:" not in url for url in urls)
    body = last_text(client)
    assert "mahdisarmad59@gmail.com" in body  # email shown as text
    assert "989305560950" in body  # phone shown as text


def test_admin_callback_tampering_is_rejected(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    disp.handle_update(callback_update(1, 500, 700, "a:students"))  # 700 is NOT an owner
    assert client.answered[-1]["show_alert"] is True
    assert client.answered[-1]["text"] == texts.ACCESS_DENIED
    assert not any(texts.ADMIN_TITLE in (s.get("text") or "") for s in client.sent)


def test_admin_entry_opens_panel_for_owner(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    disp.handle_update(callback_update(1, 500, 111, cb.ADMIN))  # 111 is an owner
    assert any(texts.ADMIN_TITLE in (s.get("text") or "") for s in client.sent)
    assert texts.BTN_ADMIN_STUDENTS in button_texts(last_markup(client))
