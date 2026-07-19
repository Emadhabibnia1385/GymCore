"""Course session derivation, attendance outcomes, corrections, auto-finish."""

from datetime import date

import pytest

from app.core.exceptions import ValidationError
from app.models import AttendanceStatus, CourseStatus
from app.services import attendance as attendance_service
from app.services import classes as classes_service
from app.services import courses as courses_service
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


def test_attendance_module_has_no_mutators():
    assert not hasattr(attendance_service, "update")
    assert not hasattr(attendance_service, "delete")


def test_renew_carries_unused_sessions(db):
    _, course = _setup(db, 10)
    _record(db, course.id, 1, AttendanceStatus.PRESENT)  # remaining 9
    new_course = courses_service.renew(db, course.id, sessions_total=10, carry_credit=True)
    assert new_course.id != course.id
    assert new_course.sessions_total == 19  # 10 new + 9 carried
    assert courses_service.get(db, course.id).status == CourseStatus.FINISHED
