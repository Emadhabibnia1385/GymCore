"""In-bot admin panel flows driven end-to-end through the dispatcher.

Owner id 111 (Telegram) is configured in conftest. Every step is a real update
(callback or message); state persists in the Dispatcher's StateStore.
"""

from sqlalchemy import select

from app.bots.common import callbacks as cb
from app.copy import admin_texts as A
from app.copy import texts
from app.models import Notification, Person, Platform, Role
from app.models.setting import KEY_CARD_NUMBER
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import identities as identities_service
from app.services import payments as payments_service
from app.services import persons as persons_service
from app.services import settings as settings_service
from tests.fakes import button_texts, callback_update, last_markup, make_dispatcher, message_update

OWNER = 111
CHAT = 900


def _open_students(disp):
    disp.handle_update(callback_update(1, CHAT, OWNER, cb.ADMIN))


def test_admin_panel_lists_all_sections(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, cb.ADMIN))
    labels = button_texts(last_markup(client))
    for expected in (
        texts.BTN_ADMIN_STUDENTS, texts.BTN_ADMIN_CLASSES, texts.BTN_ADMIN_COURSES,
        texts.BTN_ADMIN_ATTENDANCE, texts.BTN_ADMIN_PLANS, texts.BTN_ADMIN_PAYMENTS,
        texts.BTN_ADMIN_NOTIFY, texts.BTN_ADMIN_SETTINGS,
    ):
        assert expected in labels


def test_admin_create_student(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:students"))
    disp.handle_update(callback_update(2, CHAT, OWNER, "a:students:new"))
    disp.handle_update(message_update(3, CHAT, OWNER, "علی رضایی"))
    disp.handle_update(callback_update(4, CHAT, OWNER, "a:students:new_phone_skip"))
    db.expire_all()
    student = db.scalar(select(Person).where(Person.name == "علی رضایی"))
    assert student is not None
    assert student.role == Role.CLIENT
    assert any("علی رضایی" in (s.get("text") or "") for s in client.sent)


def test_admin_create_class_type(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:classes"))
    disp.handle_update(callback_update(2, CHAT, OWNER, "a:classes:new"))
    disp.handle_update(message_update(3, CHAT, OWNER, "یوگا"))
    db.expire_all()
    assert any(c.title == "یوگا" for c in classes_service.list_class_types(db))


def test_admin_create_course_then_record_attendance(db):
    disp, client = make_dispatcher()
    student = persons_service.create(db, name="شاگرد آزمون", role=Role.CLIENT)
    class_type = classes_service.list_class_types(db, only_active=True)[0]

    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:courses:new:{student.id}"))
    disp.handle_update(
        callback_update(2, CHAT, OWNER, f"a:courses:cls:{student.id}:{class_type.id}")
    )
    disp.handle_update(message_update(3, CHAT, OWNER, "8"))          # sessions
    disp.handle_update(message_update(4, CHAT, OWNER, "1000000"))    # tuition
    disp.handle_update(message_update(5, CHAT, OWNER, "0"))          # gym fee
    disp.handle_update(message_update(6, CHAT, OWNER, "2"))          # allowed absence
    disp.handle_update(message_update(7, CHAT, OWNER, "1405/04/28"))  # start (Jalali)
    db.expire_all()

    course = courses_service.list_courses(db, client_id=student.id)[0]
    assert course.sessions_total == 8
    assert course.tuition == 1_000_000
    assert course.allowed_absence == 2

    # Attendance: course → date → outcome PRESENT → skip note.
    disp.handle_update(callback_update(8, CHAT, OWNER, f"a:attend:course:{course.id}"))
    disp.handle_update(message_update(9, CHAT, OWNER, "1405/04/29"))
    disp.handle_update(callback_update(10, CHAT, OWNER, "a:attend:outcome:PRESENT"))
    disp.handle_update(callback_update(11, CHAT, OWNER, "a:attend:note_skip"))
    db.expire_all()

    assert courses_service.consumed_sessions(db, course.id) == 1
    assert courses_service.remaining_sessions(db, courses_service.get(db, course.id)) == 7


def test_admin_record_payment(db):
    disp, client = make_dispatcher()
    student = persons_service.create(db, name="پرداخت‌کننده", role=Role.CLIENT)
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=student.id, class_type_id=class_type.id, sessions_total=8,
        tuition=1_000_000,
    )

    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:pay:new:{student.id}:{course.id}"))
    disp.handle_update(message_update(2, CHAT, OWNER, "500000"))       # amount
    disp.handle_update(message_update(3, CHAT, OWNER, "1405/04/28"))    # date
    disp.handle_update(callback_update(4, CHAT, OWNER, "a:pay:kind:TUITION"))
    disp.handle_update(callback_update(5, CHAT, OWNER, "a:pay:note_skip"))
    db.expire_all()

    assert payments_service.total_paid(db, course.id) == 500_000


def test_admin_edit_setting(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:settings"))
    disp.handle_update(callback_update(2, CHAT, OWNER, "a:settings:edit:card_number"))
    disp.handle_update(message_update(3, CHAT, OWNER, "6037-1111-2222-3333"))
    db.expire_all()
    assert settings_service.get_value(db, KEY_CARD_NUMBER) == "6037-1111-2222-3333"


def test_admin_broadcast_records_notification(db):
    disp, client = make_dispatcher()
    identities_service.get_or_create_person(db, Platform.TELEGRAM, "555", "گیرنده")
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:notify:broadcast"))
    disp.handle_update(message_update(2, CHAT, OWNER, "سلام به همه 🟢"))
    disp.handle_update(callback_update(3, CHAT, OWNER, "a:notify:send"))
    db.expire_all()
    assert db.scalar(select(Notification)) is not None


def test_non_owner_message_never_enters_admin(db):
    # A non-owner cannot open admin, so their text just gets the client menu.
    disp, client = make_dispatcher()
    disp.handle_update(message_update(1, 901, 702, "hello"))
    labels = button_texts(last_markup(client))
    assert texts.BTN_ADMIN_PANEL not in labels
    assert A.STUDENTS_TITLE not in (client.sent[-1].get("text") or "")
