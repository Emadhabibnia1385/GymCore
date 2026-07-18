"""Automated reminder logic: low-session, inactivity, and de-duplication.

`now` is injected so the tests are deterministic. The suite shares one SQLite
database, so every assertion filters `scan_and_send`'s result to the course the
test created (by course_id) rather than assuming it is the only active course.
"""

from datetime import UTC, date, datetime, timedelta

from app.models import AttendanceStatus, CourseStatus, ReminderKind
from app.services import attendance as attendance_service
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import persons as persons_service
from app.services import reminders as reminders_service


def _make_course(db, phone, *, sessions_total, start_date):
    person = persons_service.create(db, name="کاربر تست", phone=phone)
    class_type = classes_service.create(db, title="بدنسازی")
    return courses_service.create(
        db,
        client_id=person.id,
        class_type_id=class_type.id,
        sessions_total=sessions_total,
        tuition=0,
        gym_fee=0,
        start_date=start_date,
    )


def _kinds_for(sent, course_id):
    return [r.kind for r in sent if r.course_id == course_id]


def test_low_session_reminder_is_sent(db, unique_phone):
    start = date(2026, 7, 1)
    course = _make_course(db, unique_phone, sessions_total=2, start_date=start)
    # today == start_date, so the course is not "inactive" — isolate low-sessions.
    sent = reminders_service.scan_and_send(db, now=datetime(2026, 7, 1, tzinfo=UTC))

    mine = [r for r in sent if r.course_id == course.id]
    assert [r.kind for r in mine] == [ReminderKind.LOW_SESSIONS]
    assert mine[0].detail == "remaining=2"


def test_healthy_course_gets_no_reminder(db, unique_phone):
    start = date(2026, 7, 1)
    course = _make_course(db, unique_phone, sessions_total=10, start_date=start)
    sent = reminders_service.scan_and_send(db, now=datetime(2026, 7, 1, tzinfo=UTC))
    assert _kinds_for(sent, course.id) == []


def test_inactive_course_reminder_is_sent(db, unique_phone):
    start = date(2026, 7, 1)
    # Plenty of sessions left (no low-session trigger), but no attendance.
    course = _make_course(db, unique_phone, sessions_total=10, start_date=start)
    sent = reminders_service.scan_and_send(db, now=datetime(2026, 7, 20, tzinfo=UTC))

    mine = [r for r in sent if r.course_id == course.id]
    assert [r.kind for r in mine] == [ReminderKind.COURSE_INACTIVE]
    assert mine[0].detail == "inactive_days=19"


def test_recent_attendance_suppresses_inactivity(db, unique_phone):
    start = date(2026, 7, 1)
    course = _make_course(db, unique_phone, sessions_total=10, start_date=start)
    attendance_service.record(db, course.id, date(2026, 7, 18), AttendanceStatus.PRESENT)
    # Last activity was 2 days before "now" — under the 10-day inactivity limit.
    sent = reminders_service.scan_and_send(db, now=datetime(2026, 7, 20, tzinfo=UTC))
    assert _kinds_for(sent, course.id) == []


def test_no_resend_within_window(db, unique_phone):
    start = date(2026, 7, 1)
    course = _make_course(db, unique_phone, sessions_total=2, start_date=start)
    first = reminders_service.scan_and_send(db, now=datetime(2026, 7, 1, tzinfo=UTC))
    assert _kinds_for(first, course.id) == [ReminderKind.LOW_SESSIONS]

    # 2 days later (< REMINDER_RESEND_DAYS=3): must not resend.
    second = reminders_service.scan_and_send(db, now=datetime(2026, 7, 3, tzinfo=UTC))
    assert _kinds_for(second, course.id) == []


def test_resend_after_window(db, unique_phone):
    start = date(2026, 7, 1)
    course = _make_course(db, unique_phone, sessions_total=2, start_date=start)
    now = datetime(2026, 7, 1, tzinfo=UTC)
    reminders_service.scan_and_send(db, now=now)

    # 3 days later (== REMINDER_RESEND_DAYS): the window has elapsed, resend.
    later = reminders_service.scan_and_send(db, now=now + timedelta(days=3))
    assert ReminderKind.LOW_SESSIONS in _kinds_for(later, course.id)


def test_paused_course_is_skipped(db, unique_phone):
    start = date(2026, 7, 1)
    course = _make_course(db, unique_phone, sessions_total=2, start_date=start)
    courses_service.set_status(db, course.id, CourseStatus.PAUSED)
    sent = reminders_service.scan_and_send(db, now=datetime(2026, 7, 1, tzinfo=UTC))
    assert _kinds_for(sent, course.id) == []
