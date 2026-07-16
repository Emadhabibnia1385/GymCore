"""Course business rules: computed remaining sessions, auto-finish."""

from datetime import date

import pytest

from app.core.exceptions import ValidationError
from app.models import AttendanceStatus, CourseStatus, Role
from app.services import attendance as attendance_service
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import persons as persons_service


@pytest.fixture()
def course(db, unique_phone):
    person = persons_service.create(db, name="علی رضایی", phone=unique_phone)
    class_type = classes_service.create(db, title="بدنسازی")
    return courses_service.create(
        db,
        client_id=person.id,
        class_type_id=class_type.id,
        sessions_total=4,
        tuition=2_000_000,
        gym_fee=500_000,
        start_date=date(2026, 7, 1),
    )


def test_remaining_sessions_only_consuming_statuses_count(db, course):
    day = date(2026, 7, 1)
    # These consume sessions:
    attendance_service.record(db, course.id, day, AttendanceStatus.PRESENT)
    attendance_service.record(db, course.id, day, AttendanceStatus.ABSENT_UNAUTHORIZED)
    # These do NOT consume sessions:
    attendance_service.record(db, course.id, day, AttendanceStatus.ABSENT_ALLOWED)
    attendance_service.record(db, course.id, day, AttendanceStatus.COACH_CANCELLED)
    attendance_service.record(db, course.id, day, AttendanceStatus.HOLIDAY)

    assert courses_service.remaining_sessions(db, course) == 2


def test_course_auto_finishes_when_sessions_exhausted(db, course):
    day = date(2026, 7, 1)
    for _ in range(4):
        attendance_service.record(db, course.id, day, AttendanceStatus.PRESENT)

    refreshed = courses_service.get(db, course.id)
    assert refreshed.status == CourseStatus.FINISHED
    assert courses_service.remaining_sessions(db, refreshed) == 0

    # No further sessions can be recorded on a finished course.
    with pytest.raises(ValidationError):
        attendance_service.record(db, course.id, day, AttendanceStatus.PRESENT)


def test_cannot_overconsume_sessions(db, course):
    day = date(2026, 7, 1)
    for _ in range(3):
        attendance_service.record(db, course.id, day, AttendanceStatus.PRESENT)
    # 1 remaining: a non-consuming event is still fine.
    attendance_service.record(db, course.id, day, AttendanceStatus.HOLIDAY)
    attendance_service.record(db, course.id, day, AttendanceStatus.PRESENT)
    # Now exhausted and auto-finished.
    with pytest.raises(ValidationError):
        attendance_service.record(db, course.id, day, AttendanceStatus.ABSENT_UNAUTHORIZED)


def test_course_validation(db, unique_phone):
    person = persons_service.create(db, name="سارا محمدی", phone=unique_phone)
    class_type = classes_service.create(db, title="TRX")
    with pytest.raises(ValidationError):
        courses_service.create(
            db,
            client_id=person.id,
            class_type_id=class_type.id,
            sessions_total=0,  # invalid
            tuition=0,
            gym_fee=0,
            start_date=date(2026, 7, 1),
        )


def test_register_from_bot_links_existing_person_by_phone(db, unique_phone):
    from app.models import Platform

    existing = persons_service.create(
        db, name="رضا کریمی", phone=unique_phone, role=Role.CLIENT
    )
    spaced_phone = f"{unique_phone[:4]} {unique_phone[4:7]} {unique_phone[7:]}"
    person = persons_service.register_from_bot(
        db, Platform.TELEGRAM, "12345", "رضا", spaced_phone
    )
    assert person.id == existing.id
    assert any(
        identity.platform == Platform.TELEGRAM
        and identity.platform_user_id == "12345"
        for identity in person.identities
    )
