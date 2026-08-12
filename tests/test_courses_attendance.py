"""Course session derivation, attendance outcomes, corrections, auto-finish."""

from datetime import date

import pytest

from app.core.exceptions import ValidationError
from app.models import AttendanceStatus, CourseStatus
from app.services import attendance as attendance_service
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import payments as payments_service
from app.services import persons as persons_service


def _setup(db, sessions_total=10, allowed=2):
    client = persons_service.create(db, name="کاربر تست")
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db,
        client_id=client.id,
        class_type_id=class_type.id,
        sessions_total=sessions_total,
        allowed_absence=allowed,
        start_date=date(2026, 7, 1),
    )
    return client, course


def _record(db, course_id, day, status):
    attendance_service.record(db, course_id, date(2026, 7, day), status, notify=False)


def test_only_present_and_unauthorized_consume(db):
    _, course = _setup(db, 10)
    _record(db, course.id, 1, AttendanceStatus.PRESENT)
    _record(db, course.id, 3, AttendanceStatus.PRESENT)
    _record(db, course.id, 5, AttendanceStatus.ABSENT_UNAUTHORIZED)
    _record(db, course.id, 7, AttendanceStatus.ABSENT_ALLOWED)
    _record(db, course.id, 9, AttendanceStatus.HOLIDAY)
    _record(db, course.id, 11, AttendanceStatus.COACH_CANCELLED)
    assert courses_service.consumed_sessions(db, course.id) == 3
    assert courses_service.remaining_sessions(db, courses_service.get(db, course.id)) == 7
    assert courses_service.allowed_absence_used(db, course.id) == 1


def test_correction_latest_event_wins(db):
    _, course = _setup(db, 10)
    _record(db, course.id, 1, AttendanceStatus.PRESENT)
    assert courses_service.consumed_sessions(db, course.id) == 1
    attendance_service.correct(
        db, course.id, date(2026, 7, 1), AttendanceStatus.HOLIDAY, created_by="111"
    )
    assert courses_service.consumed_sessions(db, course.id) == 0
    # History is preserved (both events remain).
    assert len(attendance_service.list_for_course(db, course.id)) == 2


def test_auto_finish_when_exhausted(db):
    _, course = _setup(db, 2)
    _record(db, course.id, 1, AttendanceStatus.PRESENT)
    _record(db, course.id, 3, AttendanceStatus.PRESENT)
    assert courses_service.get(db, course.id).status == CourseStatus.FINISHED


def test_cannot_record_beyond_capacity(db):
    _, course = _setup(db, 1)
    _record(db, course.id, 1, AttendanceStatus.PRESENT)  # exhausts + auto-finishes
    with pytest.raises(ValidationError):
        _record(db, course.id, 3, AttendanceStatus.PRESENT)


def test_excused_absence_is_capped_by_the_allowance(db):
    _, course = _setup(db, sessions_total=10, allowed=2)
    _record(db, course.id, 1, AttendanceStatus.ABSENT_ALLOWED)
    _record(db, course.id, 3, AttendanceStatus.ABSENT_ALLOWED)
    assert courses_service.allowed_absence_used(db, course.id) == 2

    with pytest.raises(ValidationError):  # the third one is over the ceiling
        _record(db, course.id, 5, AttendanceStatus.ABSENT_ALLOWED)

    # Past the ceiling the absence is recorded as unauthorized instead, and
    # re-marking an already-excused date stays a correction.
    _record(db, course.id, 5, AttendanceStatus.ABSENT_UNAUTHORIZED)
    _record(db, course.id, 1, AttendanceStatus.ABSENT_ALLOWED)
    assert courses_service.allowed_absence_used(db, course.id) == 2


def test_zero_allowance_means_no_limit(db):
    _, course = _setup(db, sessions_total=10, allowed=0)
    for day in (1, 3, 5):
        _record(db, course.id, day, AttendanceStatus.ABSENT_ALLOWED)
    assert courses_service.allowed_absence_used(db, course.id) == 3


def test_attendance_module_has_no_mutators():
    assert not hasattr(attendance_service, "update")
    assert not hasattr(attendance_service, "delete")


def test_attendance_report_text_lists_sessions(db):
    from app.bots.common import formatting

    _, course = _setup(db, sessions_total=4)
    _record(db, course.id, 1, AttendanceStatus.PRESENT)
    _record(db, course.id, 3, AttendanceStatus.ABSENT_UNAUTHORIZED)
    text = formatting.format_attendance_report(db, course)
    assert text is not None
    assert course.class_type.title in text
    assert "حاضر" in text

    _, empty = _setup(db, sessions_total=4)
    assert formatting.format_attendance_report(db, empty) is None  # nothing to report


def test_coach_cancel_credits_next_course(db):
    client = persons_service.create(db, name="اعتبار لغو")
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=client.id, class_type_id=class_type.id,
        sessions_total=10, tuition=900_000, gym_fee=100_000, start_date=date(2026, 7, 1),
    )
    assert courses_service.per_session_cost(course) == 100_000  # (900k + 100k) / 10

    _record(db, course.id, 1, AttendanceStatus.COACH_CANCELLED)
    new_course = courses_service.renew(db, course.id, sessions_total=10)
    # The cancelled session's cost is credited onto the next course.
    assert payments_service.total_paid(db, new_course.id) == 100_000


def test_renew_carries_unused_sessions(db):
    _, course = _setup(db, 10)
    _record(db, course.id, 1, AttendanceStatus.PRESENT)  # remaining 9
    new_course = courses_service.renew(db, course.id, sessions_total=10, carry_credit=True)
    assert new_course.id != course.id
    assert new_course.sessions_total == 19  # 10 new + 9 carried
    assert courses_service.get(db, course.id).status == CourseStatus.FINISHED
