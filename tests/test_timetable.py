"""The weekly timetable: each weekday and its classes, from the active courses."""

from datetime import date

from app.bots.common import callbacks as cb
from app.copy import admin_texts as A
from app.copy import texts
from app.models import CourseStatus, Role
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import persons as persons_service
from app.services import schedule as schedule_service
from tests.fakes import button_texts, callback_update, last_markup, last_text, make_dispatcher

OWNER = 111
CHAT = 900
START = date(2026, 7, 25)  # a Saturday (شنبه)


def _course(db, name, weekdays, class_times=None, class_time=None, status=None):
    client = persons_service.create(db, name=name, role=Role.CLIENT)
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=client.id, class_type_id=class_type.id, sessions_total=12,
        start_date=START, weekdays=weekdays, class_times=class_times, class_time=class_time,
    )
    if status is not None:
        course = courses_service.set_status(db, course.id, status)
    return course


def test_timetable_groups_active_courses_by_weekday_in_time_order(db):
    late = _course(db, "شاگرد دیر", "0,2", class_times="0@20:00,2@18:00")
    early = _course(db, "شاگرد زود", "0", class_times="0@۰۸:۳۰")  # Persian digits sort too
    _course(db, "شاگرد تمام", "0", class_times="0@07:00", status=CourseStatus.FINISHED)

    week = schedule_service.weekly_timetable(db)
    assert [(e.time, e.course.id) for e in week[0]] == [("۰۸:۳۰", early.id), ("20:00", late.id)]
    assert [e.course.id for e in week[2]] == [late.id]
    assert week[1] == [] and week[6] == []  # finished courses and empty days stay out


def test_timetable_uses_the_single_class_time_and_puts_untimed_classes_last(db):
    timed = _course(db, "با ساعت", "3", class_times="3@17:00")
    untimed = _course(db, "بی ساعت", "3")
    legacy = _course(db, "قدیمی", "3", class_time="16:00")
    tuesday = schedule_service.weekly_timetable(db)[3]
    assert [(e.time, e.course.id) for e in tuesday] == [
        ("16:00", legacy.id), ("17:00", timed.id), ("", untimed.id),
    ]


def test_admin_opens_the_week_then_a_day_table(db):
    course = _course(db, "شاگرد هفته", "0,4", class_times="0@18:30,4@19:00")
    disp, client = make_dispatcher()

    disp.handle_update(callback_update(1, CHAT, OWNER, cb.ADMIN))
    assert texts.BTN_ADMIN_WEEK in button_texts(last_markup(client))

    disp.handle_update(callback_update(2, CHAT, OWNER, "a:week"))
    body = last_text(client)
    assert A.TIMETABLE_TITLE in body
    assert "18:30 — شاگرد هفته" in body
    assert A.TIMETABLE_DAY_EMPTY in body  # یک‌شنبه has no class

    disp.handle_update(callback_update(3, CHAT, OWNER, "a:week:day:0"))
    rows = [row for row in last_markup(client)["inline_keyboard"] if len(row) == 3]
    assert [cell["text"] for cell in rows[0]] == ["18:30", "شاگرد هفته", course.class_type.title]
    assert rows[0][0]["callback_data"] == f"a:students:view:{course.client_id}"

    disp.handle_update(callback_update(4, CHAT, OWNER, "a:week:day:9"))  # tampered day
    assert A.TIMETABLE_TITLE in last_text(client)
