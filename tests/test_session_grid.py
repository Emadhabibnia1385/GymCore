"""The session grid: weekly pattern, numbering, and the extra-row rule.

The rules being pinned down here are the coach's, from the paper table:
حاضر and غیبت غیرمجاز burn a session and take the next number; غیبت مجاز /
لغو مربی / تعطیلی burn nothing and push one extra row onto the end.
"""

from datetime import date

import pytest

from app.bots.common import callbacks as cb
from app.bots.common import grid
from app.copy import admin_texts as A
from app.copy import texts
from app.models import AttendanceStatus, Platform, Role
from app.services import attendance as attendance_service
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import persons as persons_service
from app.services import schedule as schedule_service
from tests.fakes import (
    button_texts,
    callback_update,
    last_markup,
    last_text,
    make_dispatcher,
    message_update,
    register,
)

OWNER = 111
CHAT = 900

# 1405/05/03 = 2026-07-25, a Saturday (شنبه) — pattern شنبه/دوشنبه/چهارشنبه.
START = date(2026, 7, 25)
PATTERN = "0,2,4"


def _course(db, sessions_total=6, allowed=2, weekdays=PATTERN, name="شاگرد جدول"):
    client = persons_service.create(db, name=name, role=Role.CLIENT)
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db,
        client_id=client.id,
        class_type_id=class_type.id,
        sessions_total=sessions_total,
        allowed_absence=allowed,
        start_date=START,
        weekdays=weekdays,
    )
    return client, course


def _record(db, course_id, session_date, status, note=None):
    attendance_service.record(db, course_id, session_date, status, note=note, notify=False)


# --- weekday arithmetic ---


def test_persian_weekday_indexes():
    assert schedule_service.persian_weekday(START) == 0  # شنبه
    assert schedule_service.weekday_name(START) == "شنبه"
    assert schedule_service.weekday_name(date(2026, 7, 31)) == "جمعه"


def test_weekday_pattern_round_trips():
    assert schedule_service.parse_weekdays("4,0,2") == [0, 2, 4]
    assert schedule_service.format_weekdays({4, 0, 2}) == "0,2,4"
    assert schedule_service.parse_weekdays("9,x,-1") == []  # garbage is dropped
    assert schedule_service.weekdays_label(PATTERN) == "شنبه، دوشنبه، چهارشنبه"


def test_courses_without_a_pattern_fall_back_to_the_start_weekday(db):
    _, course = _course(db, weekdays=None)
    assert schedule_service.course_weekdays(course) == [0]
    slots = schedule_service.build(db, course)
    assert all(slot.date.weekday() == START.weekday() for slot in slots)


# --- grid shape ---


def test_grid_follows_the_weekly_pattern(db):
    _, course = _course(db, sessions_total=6)
    slots = schedule_service.build(db, course)
    assert len(slots) == 6
    assert [s.date for s in slots[:4]] == [
        date(2026, 7, 25),  # شنبه
        date(2026, 7, 27),  # دوشنبه
        date(2026, 7, 29),  # چهارشنبه
        date(2026, 8, 1),   # شنبه
    ]
    assert [s.weekday for s in slots[:3]] == ["شنبه", "دوشنبه", "چهارشنبه"]
    assert all(slot.status is None and not slot.recorded for slot in slots)


def test_pending_slots_render_as_waiting(db):
    _, course = _course(db)
    slots = schedule_service.build(db, course)
    assert grid.status_cell(slots[0]) == grid.PENDING_CELL


def test_numbering_counts_only_consuming_outcomes(db):
    _, course = _course(db, sessions_total=6)
    _record(db, course.id, date(2026, 7, 25), AttendanceStatus.PRESENT)
    _record(db, course.id, date(2026, 7, 27), AttendanceStatus.ABSENT_ALLOWED)
    _record(db, course.id, date(2026, 7, 29), AttendanceStatus.PRESENT)
    _record(db, course.id, date(2026, 8, 1), AttendanceStatus.ABSENT_UNAUTHORIZED)

    slots = schedule_service.build(db, course)
    assert [s.session_no for s in slots[:4]] == [1, None, 2, 3]
    assert grid.status_cell(slots[0]) == "✅ جلسه 1"
    assert grid.status_cell(slots[1]) == "🟡 غیبت مجاز"
    assert grid.status_cell(slots[3]) == "🔴 غایب 3"


def test_allowed_absence_adds_an_extra_row(db):
    """غیبت مجاز doesn't burn a session, so the client gets one more date."""
    _, course = _course(db, sessions_total=6)
    assert len(schedule_service.build(db, course)) == 6

    _record(db, course.id, date(2026, 7, 25), AttendanceStatus.ABSENT_ALLOWED)
    slots = schedule_service.build(db, course)
    assert len(slots) == 7  # one recorded + six still owed
    assert sum(1 for s in slots if not s.recorded) == 6
    assert courses_service.remaining_sessions(db, course) == 6


def test_unauthorized_absence_does_not_add_a_row(db):
    _, course = _course(db, sessions_total=6)
    _record(db, course.id, date(2026, 7, 25), AttendanceStatus.ABSENT_UNAUTHORIZED)
    slots = schedule_service.build(db, course)
    assert len(slots) == 6
    assert courses_service.remaining_sessions(db, course) == 5


def test_holiday_and_coach_cancellation_also_extend_the_grid(db):
    _, course = _course(db, sessions_total=4)
    _record(db, course.id, date(2026, 7, 25), AttendanceStatus.HOLIDAY)
    _record(db, course.id, date(2026, 7, 27), AttendanceStatus.COACH_CANCELLED)
    slots = schedule_service.build(db, course)
    assert len(slots) == 6
    assert courses_service.remaining_sessions(db, course) == 4


def test_off_schedule_session_is_merged_by_date(db):
    """A make-up session on a non-pattern day still shows up, in date order."""
    _, course = _course(db, sessions_total=4)
    _record(db, course.id, date(2026, 7, 26), AttendanceStatus.PRESENT)  # یک‌شنبه
    slots = schedule_service.build(db, course)
    assert slots[0].date == date(2026, 7, 26)
    assert slots[0].session_no == 1
    assert slots[1].date > date(2026, 7, 26)


def test_correction_renumbers_the_grid(db):
    _, course = _course(db, sessions_total=6)
    _record(db, course.id, date(2026, 7, 25), AttendanceStatus.PRESENT)
    _record(db, course.id, date(2026, 7, 27), AttendanceStatus.PRESENT)
    # The coach re-taps the first row and marks it مجاز instead.
    attendance_service.correct(
        db, course.id, date(2026, 7, 25), AttendanceStatus.ABSENT_ALLOWED, created_by="111"
    )
    slots = schedule_service.build(db, course)
    assert [s.session_no for s in slots[:2]] == [None, 1]
    assert len(attendance_service.list_for_course(db, course.id)) == 3  # history intact


def test_summary_counts_every_outcome(db):
    _, course = _course(db, sessions_total=5)
    _record(db, course.id, date(2026, 7, 25), AttendanceStatus.PRESENT)
    _record(db, course.id, date(2026, 7, 27), AttendanceStatus.ABSENT_ALLOWED)
    _record(db, course.id, date(2026, 7, 29), AttendanceStatus.ABSENT_UNAUTHORIZED)
    stats = schedule_service.summary(db, course)
    assert stats["consumed"] == 2
    assert stats["remaining"] == 3
    assert stats["present"] == 1
    assert stats["absent_allowed"] == 1
    assert stats["absent_unauthorized"] == 1


# --- rendering ---


def test_grid_rows_have_three_cells_sharing_one_callback(db):
    _, course = _course(db, sessions_total=3)
    slots = schedule_service.build(db, course)
    rows = grid.rows(slots, lambda slot: f"a:attend:slot:{course.id}:{grid.date_token(slot.date)}")
    assert all(len(row) == 3 for row in rows)
    first = rows[0]
    assert first[0]["text"] == "شنبه"
    assert first[2]["text"] == grid.PENDING_CELL
    assert len({cell["callback_data"] for cell in first}) == 1  # whole row = one target


def test_client_grid_cells_are_inert(db):
    _, course = _course(db, sessions_total=3)
    rows = grid.client_rows(schedule_service.build(db, course))
    assert all(cell["callback_data"] == cb.NOOP for row in rows for cell in row)


def test_grid_paginates_long_courses(db):
    _, course = _course(db, sessions_total=20)
    slots = schedule_service.build(db, course)
    visible, page, pages = grid.page_slice(slots, 2)
    assert pages == 3 and page == 2
    assert len(visible) == grid.ROWS_PER_PAGE


def test_default_page_lands_on_the_next_pending_session(db):
    _, course = _course(db, sessions_total=20)
    for offset in range(0, 20, 2):  # fill the first 10 scheduled dates
        slot = schedule_service.build(db, course)[offset // 2]
        if slot.recorded:
            continue
        _record(db, course.id, slot.date, AttendanceStatus.PRESENT)
    slots = schedule_service.build(db, course)
    pending = schedule_service.next_pending(slots)
    assert grid.default_page(slots) == grid.page_of(slots, pending.date)


def test_callback_data_stays_within_telegram_limit(db):
    _, course = _course(db, sessions_total=3)
    slot = schedule_service.build(db, course)[0]
    token = grid.date_token(slot.date)
    for data in (
        f"a:attend:slot:{course.id}:{token}",
        f"a:attend:set:{course.id}:{token}:U",
        f"a:attend:note:{course.id}:{token}",
        cb.schedule(course.id, 9),
    ):
        assert len(data.encode()) <= 64


def test_date_token_rejects_tampered_values():
    assert grid.parse_date_token("20260725") == date(2026, 7, 25)
    for bad in ("", "2026072", "abcdefgh", "20261345", "-2026072"):
        assert grid.parse_date_token(bad) is None


# --- admin panel wiring ---


def test_admin_menu_has_plans_not_courses(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, cb.ADMIN))
    labels = [b["text"] for row in last_markup(client)["inline_keyboard"] for b in row]
    assert labels[0] == texts.BTN_ADMIN_CLASSES
    assert texts.BTN_ADMIN_PLANS in labels
    assert texts.BTN_ADMIN_STUDENTS in labels
    assert texts.BTN_ADMIN_COURSES not in labels  # «مدیریت دوره‌ها» removed (empty)


def test_student_profile_is_that_students_menu(db):
    disp, client = make_dispatcher()
    student, course = _course(db, name="شاگرد منو")
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:students:view:{student.id}"))
    labels = button_texts(last_markup(client))
    assert A.BTN_STUDENT_GRID in labels  # active course → grid is the primary action
    for expected in (A.BTN_COURSES, A.BTN_PROGRAMS, A.BTN_PAYMENTS, A.BTN_ATTENDANCE):
        assert expected in labels
    assert "شاگرد منو" in last_text(client)


def test_student_without_a_course_is_offered_one(db):
    disp, client = make_dispatcher()
    student = persons_service.create(db, name="بدون دوره", role=Role.CLIENT)
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:students:view:{student.id}"))
    labels = button_texts(last_markup(client))
    assert A.BTN_NEW_COURSE_FOR in labels
    assert A.NO_ACTIVE_COURSE in last_text(client)


def test_admin_toggles_student_active_state(db):
    disp, client = make_dispatcher()
    student, _ = _course(db, name="شاگرد توقف")
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:students:toggle:{student.id}"))
    db.expire_all()
    assert persons_service.get(db, student.id).is_active is False
    disp.handle_update(callback_update(2, CHAT, OWNER, f"a:students:toggle:{student.id}"))
    db.expire_all()
    assert persons_service.get(db, student.id).is_active is True


def test_admin_records_an_allowed_absence_from_the_grid(db):
    disp, client = make_dispatcher()
    _, course = _course(db, sessions_total=6, name="شاگرد ثبت")
    slot = schedule_service.build(db, course)[0]
    token = grid.date_token(slot.date)

    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:attend:course:{course.id}"))
    assert A.GRID_HINT in last_text(client)

    disp.handle_update(callback_update(2, CHAT, OWNER, f"a:attend:slot:{course.id}:{token}"))
    assert grid.PICKER_LABELS[AttendanceStatus.PRESENT] in button_texts(last_markup(client))

    disp.handle_update(callback_update(3, CHAT, OWNER, f"a:attend:set:{course.id}:{token}:A"))
    db.expire_all()
    assert courses_service.allowed_absence_used(db, course.id) == 1
    assert courses_service.remaining_sessions(db, courses_service.get(db, course.id)) == 6
    assert len(schedule_service.build(db, courses_service.get(db, course.id))) == 7


def test_admin_note_is_staged_then_saved_with_the_outcome(db):
    disp, client = make_dispatcher()
    _, course = _course(db, sessions_total=4, name="شاگرد یادداشت")
    token = grid.date_token(schedule_service.build(db, course)[0].date)

    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:attend:note:{course.id}:{token}"))
    disp.handle_update(message_update(2, CHAT, OWNER, "مسافرت"))
    assert "مسافرت" in last_text(client)  # staged, shown back before the outcome
    disp.handle_update(callback_update(3, CHAT, OWNER, f"a:attend:set:{course.id}:{token}:A"))
    db.expire_all()

    events = attendance_service.list_for_course(db, course.id)
    assert [e.note for e in events] == ["مسافرت"]
    assert events[0].created_by == str(OWNER)


def test_admin_can_record_an_off_schedule_session(db):
    disp, client = make_dispatcher()
    _, course = _course(db, sessions_total=4, name="شاگرد جبرانی")
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:attend:extra:{course.id}"))
    disp.handle_update(message_update(2, CHAT, OWNER, "1405/05/04"))  # 2026-07-26, یک‌شنبه
    token = grid.date_token(date(2026, 7, 26))
    disp.handle_update(callback_update(3, CHAT, OWNER, f"a:attend:set:{course.id}:{token}:P"))
    db.expire_all()
    assert courses_service.consumed_sessions(db, course.id) == 1


def test_exhausted_course_reports_on_the_grid_instead_of_erroring(db):
    disp, client = make_dispatcher()
    _, course = _course(db, sessions_total=1, name="شاگرد پایان")
    slots = schedule_service.build(db, course)
    _record(db, course.id, slots[0].date, AttendanceStatus.PRESENT)  # auto-finishes

    token = grid.date_token(date(2026, 8, 5))
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:attend:set:{course.id}:{token}:P"))
    body = last_text(client)
    assert "⚠️" in body
    assert texts.GRID_TITLE in body  # the grid is still on screen


def test_tampered_grid_callbacks_do_not_crash(db):
    disp, client = make_dispatcher()
    _, course = _course(db, sessions_total=4, name="شاگرد دستکاری")
    for data in (
        "a:attend:slot:abc:20260725",
        f"a:attend:slot:{course.id}:99999999",
        f"a:attend:set:{course.id}:20260725:ZZ",
        "a:attend:set:::",
    ):
        disp.handle_update(callback_update(1, CHAT, OWNER, data))
    assert client.sent  # every one produced a screen, none raised


# --- client side ---


def test_client_sees_the_same_grid_read_only(db):
    disp, client = make_dispatcher()
    register(disp, 902, 707)
    student = persons_service.find_by_platform_id(db, Platform.TELEGRAM, "707")
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=student.id, class_type_id=class_type.id, sessions_total=4,
        start_date=START, weekdays=PATTERN,
    )
    _record(db, course.id, date(2026, 7, 25), AttendanceStatus.PRESENT)

    disp.handle_update(callback_update(1, 902, 707, cb.course(course.id)))
    assert texts.BTN_SCHEDULE in button_texts(last_markup(client))

    disp.handle_update(callback_update(2, 902, 707, cb.schedule(course.id)))
    body, markup = last_text(client), last_markup(client)
    assert texts.GRID_TITLE in body
    assert "✅ جلسه 1" in button_texts(markup)
    assert any(cell["callback_data"] == cb.NOOP for row in markup["inline_keyboard"]
               for cell in row)


def test_client_cannot_open_another_clients_grid(db):
    disp, client = make_dispatcher()
    _, course = _course(db, sessions_total=4, name="شاگرد دیگر")
    register(disp, 903, 708)
    disp.handle_update(callback_update(1, 903, 708, cb.schedule(course.id)))
    assert texts.NOT_FOUND in last_text(client)


@pytest.mark.parametrize("platform", [Platform.TELEGRAM, Platform.BALE])
def test_grid_renders_on_both_platforms(db, platform):
    disp, client = make_dispatcher(platform)
    owner = OWNER if platform == Platform.TELEGRAM else 333
    _, course = _course(db, sessions_total=4, name=f"شاگرد {platform.value}")
    disp.handle_update(callback_update(1, CHAT, owner, f"a:attend:course:{course.id}"))
    rows = last_markup(client)["inline_keyboard"]
    assert texts.GRID_TITLE in last_text(client)
    # Four session rows of three cells each, then the extra/back controls.
    assert [len(row) for row in rows[:4]] == [3, 3, 3, 3]
    assert all(cell["callback_data"].startswith("a:attend:slot:")
               for row in rows[:4] for cell in row)
