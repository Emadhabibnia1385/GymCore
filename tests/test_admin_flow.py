"""In-bot admin panel flows driven end-to-end through the dispatcher.

Owner id 111 (Telegram) is configured in conftest. Every step is a real update
(callback or message); state persists in the Dispatcher's StateStore.
"""

from datetime import date, timedelta

from sqlalchemy import func, select

from app.bots.common import callbacks as cb
from app.bots.common import grid
from app.copy import admin_texts as A
from app.copy import texts
from app.models import (
    AttendanceStatus,
    Course,
    CourseStatus,
    Notification,
    Payment,
    PaymentKind,
    Person,
    Platform,
    Role,
)
from app.models.setting import KEY_CARD_NUMBER, KEY_MAIN_INTRO
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import identities as identities_service
from app.services import payments as payments_service
from app.services import persons as persons_service
from app.services import schedule as schedule_service
from app.services import settings as settings_service
from tests.fakes import (
    button_texts,
    callback_update,
    last_markup,
    make_dispatcher,
    message_update,
    photo_message_update,
    register,
)

OWNER = 111
CHAT = 900


def _open_students(disp):
    disp.handle_update(callback_update(1, CHAT, OWNER, cb.ADMIN))


def test_admin_panel_lists_all_sections(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, cb.ADMIN))
    labels = button_texts(last_markup(client))
    for expected in (
        texts.BTN_ADMIN_STUDENTS, texts.BTN_ADMIN_CLASSES, texts.BTN_ADMIN_PLANS,
        texts.BTN_ADMIN_ATTENDANCE, texts.BTN_ADMIN_PAYMENTS,
        texts.BTN_ADMIN_NOTIFY, texts.BTN_ADMIN_SETTINGS, texts.BTN_ADMIN_START,
    ):
        assert expected in labels
    assert texts.BTN_ADMIN_COURSES not in labels  # «مدیریت دوره‌ها» removed (empty)


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
    # Weekly pattern: pre-selected with the start date's weekday, plus چهارشنبه.
    disp.handle_update(callback_update(8, CHAT, OWNER, "a:courses:wd:4"))
    disp.handle_update(callback_update(9, CHAT, OWNER, "a:courses:wd_done"))
    # Per-day time editor: set چهارشنبه (index 4) to 18:30, then confirm.
    disp.handle_update(callback_update(10, CHAT, OWNER, "a:courses:time_day:4"))
    disp.handle_update(message_update(11, CHAT, OWNER, "18:30"))
    disp.handle_update(callback_update(12, CHAT, OWNER, "a:courses:times_done"))
    db.expire_all()

    course = courses_service.list_courses(db, client_id=student.id)[0]
    assert course.sessions_total == 8
    assert course.tuition == 1_000_000
    assert course.allowed_absence == 2
    assert schedule_service.parse_day_times(course.class_times).get(4) == "18:30"
    assert 4 in schedule_service.parse_weekdays(course.weekdays)

    # Attendance via the session grid: open the grid, tap a row, pick ✅ حاضر.
    disp.handle_update(callback_update(13, CHAT, OWNER, f"a:attend:course:{course.id}"))
    first = schedule_service.build(db, course)[0]
    token = grid.date_token(first.date)
    disp.handle_update(callback_update(14, CHAT, OWNER, f"a:attend:slot:{course.id}:{token}"))
    disp.handle_update(callback_update(15, CHAT, OWNER, f"a:attend:set:{course.id}:{token}:P"))
    db.expire_all()

    assert courses_service.consumed_sessions(db, course.id) == 1
    assert courses_service.remaining_sessions(db, courses_service.get(db, course.id)) == 7


def test_admin_cannot_mark_future_session(db):
    disp, client = make_dispatcher()
    student = persons_service.create(db, name="آیندهٔ دور", role=Role.CLIENT)
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=student.id, class_type_id=class_type.id, sessions_total=8,
    )
    future = date.today() + timedelta(days=14)
    token = grid.date_token(future)

    # Opening a future session shows a «not yet arrived» notice, no outcome buttons.
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:attend:slot:{course.id}:{token}"))
    labels = button_texts(last_markup(client))
    assert grid.PICKER_LABELS[AttendanceStatus.PRESENT] not in labels
    assert any(A.ATTEND_FUTURE in (s.get("text") or "") for s in client.sent)

    # Even a direct set callback (a stale tap) records nothing.
    disp.handle_update(callback_update(2, CHAT, OWNER, f"a:attend:set:{course.id}:{token}:P"))
    db.expire_all()
    assert courses_service.consumed_sessions(db, course.id) == 0


def test_admin_quick_renew_resets_sessions(db):
    disp, client = make_dispatcher()
    student = persons_service.create(db, name="تمدید سریع", role=Role.CLIENT)
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=student.id, class_type_id=class_type.id,
        sessions_total=8, tuition=600_000, gym_fee=50_000, weekdays="0,2",
    )
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:courses:renew:{course.id}"))
    disp.handle_update(callback_update(2, CHAT, OWNER, f"a:courses:renew_go:{course.id}"))
    db.expire_all()

    assert courses_service.get(db, course.id).status == CourseStatus.FINISHED
    new_course = next(
        c for c in courses_service.list_courses(db, client_id=student.id) if c.id != course.id
    )
    assert new_course.status == CourseStatus.ACTIVE
    assert new_course.sessions_total == 8  # same terms, reset
    assert new_course.tuition == 600_000
    assert new_course.gym_fee == 50_000
    assert courses_service.remaining_sessions(db, new_course) == 8


def test_admin_finish_then_reactivate_course(db):
    disp, client = make_dispatcher()
    student = persons_service.create(db, name="فعال‌سازی مجدد", role=Role.CLIENT)
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=student.id, class_type_id=class_type.id, sessions_total=8,
    )
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:courses:status:{course.id}:FINISHED"))
    db.expire_all()
    assert courses_service.get(db, course.id).status == CourseStatus.FINISHED
    assert A.BTN_REACTIVATE_COURSE in button_texts(last_markup(client))  # reversible

    disp.handle_update(callback_update(2, CHAT, OWNER, f"a:courses:status:{course.id}:ACTIVE"))
    db.expire_all()
    assert courses_service.get(db, course.id).status == CourseStatus.ACTIVE


def test_admin_edit_course_fees(db):
    disp, client = make_dispatcher()
    student = persons_service.create(db, name="ویرایش هزینه", role=Role.CLIENT)
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=student.id, class_type_id=class_type.id,
        sessions_total=8, tuition=500_000, gym_fee=0,
    )
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:courses:edit_tuition:{course.id}"))
    disp.handle_update(message_update(2, CHAT, OWNER, "750000"))
    disp.handle_update(callback_update(3, CHAT, OWNER, f"a:courses:edit_gym:{course.id}"))
    disp.handle_update(message_update(4, CHAT, OWNER, "120000"))
    db.expire_all()

    updated = courses_service.get(db, course.id)
    assert updated.tuition == 750_000
    assert updated.gym_fee == 120_000


def test_admin_delete_course(db):
    disp, client = make_dispatcher()
    student = persons_service.create(db, name="حذف دوره", role=Role.CLIENT)
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=student.id, class_type_id=class_type.id, sessions_total=8,
    )
    payments_service.record(
        db, person_id=student.id, amount=200_000, kind=PaymentKind.TUITION,
        paid_at=date(2026, 7, 1), course_id=course.id, notify=False,
    )
    cid = course.id

    # Delete via admin: open confirmation, then confirm.
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:courses:del_confirm:{cid}"))
    disp.handle_update(callback_update(2, CHAT, OWNER, f"a:courses:del:{cid}"))
    db.expire_all()

    assert db.get(Course, cid) is None
    # Payment survives as a person-level record; its course link is cleared.
    payment = db.scalar(select(Payment).where(Payment.person_id == student.id))
    assert payment is not None
    assert payment.course_id is None


def test_admin_edit_course_per_day_times(db):
    disp, client = make_dispatcher()
    student = persons_service.create(db, name="ویرایش ساعت", role=Role.CLIENT)
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=student.id, class_type_id=class_type.id,
        sessions_total=6, weekdays="0,2", start_date=date(2026, 7, 25),
    )
    # Edit the schedule: open the day editor, confirm days, set شنبه (0) = 20:00.
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:courses:wdedit:{course.id}"))
    disp.handle_update(callback_update(2, CHAT, OWNER, "a:courses:wd_done"))
    disp.handle_update(callback_update(3, CHAT, OWNER, "a:courses:time_day:0"))
    disp.handle_update(message_update(4, CHAT, OWNER, "20:00"))
    disp.handle_update(callback_update(5, CHAT, OWNER, "a:courses:times_done"))
    db.expire_all()

    times = schedule_service.parse_day_times(courses_service.get(db, course.id).class_times)
    assert times.get(0) == "20:00"


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


def test_admin_set_start_text(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:start:text"))
    disp.handle_update(message_update(2, CHAT, OWNER, "به باشگاه ما خوش آمدی 🟢"))
    db.expire_all()
    assert settings_service.get_value(db, KEY_MAIN_INTRO) == "به باشگاه ما خوش آمدی 🟢"


def test_admin_set_start_poster(db):
    disp, client = make_dispatcher(Platform.TELEGRAM)
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:start:poster"))
    disp.handle_update(photo_message_update(2, CHAT, OWNER, file_id="POSTER123"))
    db.expire_all()
    key = settings_service.start_poster_key(Platform.TELEGRAM)
    assert settings_service.get_value(db, key) == "POSTER123"


def test_students_list_two_buttons_sorted_by_remaining(db):
    disp, client = make_dispatcher()
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    five = persons_service.create(db, name="پنج‌جلسه", role=Role.CLIENT)
    courses_service.create(db, client_id=five.id, class_type_id=class_type.id, sessions_total=5)
    two = persons_service.create(db, name="دوجلسه", role=Role.CLIENT)
    courses_service.create(db, client_id=two.id, class_type_id=class_type.id, sessions_total=2)

    disp.handle_update(callback_update(1, CHAT, OWNER, "a:students"))
    rows = last_markup(client)["inline_keyboard"]
    student_rows = [r for r in rows if len(r) == 2 and "جلسه" in r[1]["text"]]
    names = [r[0]["text"] for r in student_rows]
    assert names.index("دوجلسه") < names.index("پنج‌جلسه")  # fewer remaining first
    two_row = next(r for r in student_rows if r[0]["text"] == "دوجلسه")
    assert "2" in two_row[1]["text"]  # remaining-sessions button shows the count


def test_admin_delete_student_cascades(db):
    disp, client = make_dispatcher()
    student = persons_service.create(db, name="شاگرد حذفی", role=Role.CLIENT)
    sid = student.id
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=sid, class_type_id=class_type.id, sessions_total=4
    )
    payments_service.record(
        db, person_id=sid, amount=100_000, kind=PaymentKind.TUITION,
        paid_at=date(2026, 7, 1), course_id=course.id, notify=False,
    )
    # Delete via admin: confirmation, then confirm.
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:students:del_confirm:{sid}"))
    disp.handle_update(callback_update(2, CHAT, OWNER, f"a:students:del:{sid}"))
    db.expire_all()
    assert db.get(Person, sid) is None
    assert db.scalar(select(func.count()).select_from(Course).where(Course.client_id == sid)) == 0
    assert db.scalar(select(func.count()).select_from(Payment).where(Payment.person_id == sid)) == 0


def test_admin_edit_student_name_and_second_phone(db):
    disp, client = make_dispatcher()
    student = persons_service.create(db, name="نام قدیم", role=Role.CLIENT)
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:students:edit_name:{student.id}"))
    disp.handle_update(message_update(2, CHAT, OWNER, "نام جدید"))
    disp.handle_update(callback_update(3, CHAT, OWNER, f"a:students:edit_phone2:{student.id}"))
    disp.handle_update(message_update(4, CHAT, OWNER, "09121112233"))
    db.expire_all()

    updated = persons_service.get(db, student.id)
    assert updated.name == "نام جدید"
    assert updated.phone2 and "1112233" in updated.phone2


def test_admin_send_private_message_to_student(db):
    disp, client = make_dispatcher()
    student = identities_service.get_or_create_person(db, Platform.TELEGRAM, "7788", "شاگرد پیام")
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:students:msg:{student.id}"))
    disp.handle_update(message_update(2, CHAT, OWNER, "فردا کلاس تعطیل است"))
    db.expire_all()
    assert any(A.MESSAGE_SENT in (s.get("text") or "") for s in client.sent)


def test_non_owner_message_never_enters_admin(db):
    # A non-owner cannot open admin, so their text just gets the client menu.
    disp, client = make_dispatcher()
    register(disp, 901, 702)
    disp.handle_update(message_update(1, 901, 702, "hello"))
    labels = button_texts(last_markup(client))
    assert texts.BTN_ADMIN_PANEL not in labels
    assert A.STUDENTS_TITLE not in (client.sent[-1].get("text") or "")
