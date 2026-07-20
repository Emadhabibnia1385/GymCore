"""Client bot flow: phone registration, inline menus, register→contact,
order→URL, courses, programs, contact, admin-button visibility / tamper."""

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
    register,
    web_app_urls,
)


def _copy_values(markup: dict) -> list[str]:
    return [
        b["copy_text"]["text"]
        for row in markup["inline_keyboard"] for b in row if "copy_text" in b
    ]


def test_first_contact_asks_for_phone(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    disp.handle_update(message_update(1, 500, 700, "/start"))
    # No menu yet — a phone is requested with a share-contact reply keyboard.
    assert "شماره" in last_text(client)
    assert client.sent[-1]["reply_markup"].get("keyboard")  # reply keyboard, not inline


def test_registration_by_phone_then_menu(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    register(disp, 500, 700)  # shares a phone
    labels = button_texts(last_markup(client))
    assert texts.BTN_REGISTER_CLASS in labels
    assert texts.BTN_ADMIN_PANEL not in labels  # normal client
    db.expire_all()
    person = identities_service.find_person(db, Platform.TELEGRAM, "700")
    assert person is not None
    assert person.phone  # phone captured for cross-platform sync


def test_owner_bypasses_phone_and_sees_admin_button(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    disp.handle_update(message_update(1, 500, 111, "/start"))  # 111 is a configured owner
    assert texts.BTN_ADMIN_PANEL in button_texts(last_markup(client))
    db.expire_all()
    assert identities_service.find_person(db, Platform.TELEGRAM, "111").role.value == "COACH"


def test_same_phone_links_telegram_and_bale_to_one_person(db):
    tg, _ = make_dispatcher(Platform.TELEGRAM)
    register(tg, 500, 700, phone="09121112233")
    bale, _ = make_dispatcher(Platform.BALE)
    register(bale, 600, 900, phone="09121112233")  # different account, same phone
    db.expire_all()
    tg_person = identities_service.find_person(db, Platform.TELEGRAM, "700")
    bale_person = identities_service.find_person(db, Platform.BALE, "900")
    assert tg_person.id == bale_person.id  # one Person, two platform accounts


def test_start_menu_shows_poster_when_set(db):
    settings_service.set_value(
        db, settings_service.start_poster_key(Platform.TELEGRAM), "POSTERXYZ"
    )
    disp, client = make_dispatcher(Platform.TELEGRAM)
    register(disp, 500, 700)
    last = client.sent[-1]
    assert last["method"] == "send_photo_id"  # menu sent as a photo (poster)
    assert last["file_id"] == "POSTERXYZ"
    assert last["reply_markup"] is not None


def test_no_request_models_exist():
    for name in ("ClassRequest", "PlanRequest", "ClassRegistrationRequest", "RequestStatus"):
        assert not hasattr(models, name)


def test_register_shows_contact_links_not_a_form(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    register(disp, 500, 700)
    client.sent.clear()
    disp.handle_update(callback_update(1, 500, 700, cb.REGISTER))
    body = last_text(client)
    assert settings_service.get_value(db, KEY_REGISTER_CONTACT_TEXT) in body
    urls = button_urls(last_markup(client))
    assert any(u.startswith("https://t.me/") for u in urls)


def test_order_button_is_a_plain_url_link_on_both_platforms(db):
    for platform, user in ((Platform.TELEGRAM, 700), (Platform.BALE, 900)):
        disp, client = make_dispatcher(platform)
        register(disp, 500, user)
        markup = last_markup(client)
        assert not web_app_urls(markup)  # a plain link — never a Mini App
        assert any("mahdisarmad.ir/signup" in url for url in button_urls(markup))


def test_telegram_menu_buttons_carry_colour_styles(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    register(disp, 500, 700)
    styles = {
        b["text"]: b.get("style")
        for row in last_markup(client)["inline_keyboard"]
        for b in row
    }
    assert styles[texts.BTN_REGISTER_CLASS] == "primary"  # blue
    assert styles[texts.BTN_MY_CLASSES] == "success"  # green
    assert styles[texts.BTN_CONTACT] == "danger"  # red


def test_bale_menu_buttons_have_no_style(db):
    disp, client = make_dispatcher(Platform.BALE)
    register(disp, 500, 900)
    for row in last_markup(client)["inline_keyboard"]:
        for button in row:
            assert "style" not in button


def test_my_courses_empty_state_shows_contact_links(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    register(disp, 500, 700)
    client.sent.clear()
    disp.handle_update(callback_update(1, 500, 700, cb.COURSES))
    assert last_text(client) == texts.NO_COURSES
    markup = last_markup(client)
    assert any("wa.me" in u for u in button_urls(markup))  # contact links shown
    assert markup["inline_keyboard"][-1][0]["style"] == "danger"  # red back


def test_my_programs_empty_state_shows_order_button(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    register(disp, 500, 700)
    client.sent.clear()
    disp.handle_update(callback_update(1, 500, 700, cb.PROGRAMS))
    assert last_text(client) == texts.NO_PROGRAMS
    markup = last_markup(client)
    order = markup["inline_keyboard"][0][0]  # blue «سفارش برنامه» button
    assert order["style"] == "primary"
    assert "mahdisarmad.ir/signup" in order["url"]
    assert markup["inline_keyboard"][-1][0]["style"] == "danger"  # red back


def test_my_courses_list_and_detail_derive_remaining(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    register(disp, 500, 700)
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
    register(disp, 500, 700)
    register(disp, 501, 800)  # a second, different client
    db.expire_all()
    person_a = identities_service.find_person(db, Platform.TELEGRAM, "700")
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=person_a.id, class_type_id=class_type.id,
        sessions_total=5, start_date=date(2026, 7, 1),
    )
    client.sent.clear()
    disp.handle_update(callback_update(2, 501, 800, cb.course(course.id)))
    assert last_text(client) == texts.NOT_FOUND


def test_programs_list_and_file_delivery(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    register(disp, 500, 700)
    db.expire_all()
    person = identities_service.find_person(db, Platform.TELEGRAM, "700")
    training = plans_service.create_type(db, title="برنامه تمرینی", key="tr")
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


def test_contact_us_telegram_copy_buttons_alternating_colours(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    register(disp, 500, 700)
    client.sent.clear()
    disp.handle_update(callback_update(1, 500, 700, cb.CONTACT))
    assert last_text(client) != texts.ERROR
    markup = last_markup(client)
    assert all("mailto:" not in u and "tel:" not in u for u in button_urls(markup))
    copies = _copy_values(markup)
    assert "mahdisarmad59@gmail.com" in copies  # email is tap-to-copy
    assert any("09305560950" in v for v in copies)  # phone is tap-to-copy
    assert any("wa.me" in u for u in button_urls(markup))  # https links are buttons
    rows = markup["inline_keyboard"]
    assert rows[-1][0]["style"] == "danger"  # red back
    assert {b.get("style") for row in rows[:-1] for b in row} == {"primary", "success"}


def test_contact_us_bale_keeps_tel_mailto_as_text_no_style(db):
    disp, client = make_dispatcher(Platform.BALE)
    register(disp, 500, 900)
    client.sent.clear()
    disp.handle_update(callback_update(1, 500, 900, cb.CONTACT))
    body = last_text(client)
    assert "mahdisarmad59@gmail.com" in body  # email as text
    assert "09305560950" in body  # phone as text
    markup = last_markup(client)
    assert not _copy_values(markup)  # Bale gets no copy buttons
    for row in markup["inline_keyboard"]:
        for button in row:
            assert "style" not in button
    assert any("wa.me" in u for u in button_urls(markup))  # https links still buttons


def test_admin_callback_tampering_is_rejected(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    register(disp, 500, 700)  # a registered but non-owner client
    client.sent.clear()
    disp.handle_update(callback_update(1, 500, 700, "a:students"))
    assert client.answered[-1]["show_alert"] is True
    assert client.answered[-1]["text"] == texts.ACCESS_DENIED
    assert not any(texts.ADMIN_TITLE in (s.get("text") or "") for s in client.sent)


def test_user_message_is_deleted_for_single_message_ux(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    register(disp, 500, 700)
    client.deleted.clear()
    disp.handle_update(message_update(77, 500, 700, "چیزی"))
    assert 10 in client.deleted  # the user's message (message_id=10) was removed


def test_bale_navigation_replaces_previous_screen(db):
    disp, client = make_dispatcher(Platform.BALE)
    register(disp, 500, 900)  # menu shown (fresh)
    menu_id = client.sent[-1]["message_id"]
    client.deleted.clear()
    disp.handle_update(callback_update(1, 500, 900, cb.CONTACT))
    assert menu_id in client.deleted  # previous screen deleted → single message


def test_telegram_navigation_edits_in_place(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    register(disp, 500, 700)
    menu_id = client.sent[-1]["message_id"]
    client.sent.clear()
    client.deleted.clear()
    disp.handle_update(callback_update(1, 500, 700, cb.CONTACT, message_id=menu_id))
    assert client.sent[-1]["method"] == "edit_message_text"  # same message reused
    assert client.sent[-1]["message_id"] == menu_id
    assert not client.deleted


def test_admin_entry_opens_panel_for_owner(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    disp.handle_update(callback_update(1, 500, 111, cb.ADMIN))  # 111 is an owner
    assert any(texts.ADMIN_TITLE in (s.get("text") or "") for s in client.sent)
    assert texts.BTN_ADMIN_STUDENTS in button_texts(last_markup(client))
