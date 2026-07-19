"""Course management.

Core rule: remaining sessions are ALWAYS computed from attendance history,
never stored. Only PRESENT and ABSENT_UNAUTHORIZED consume sessions.

Attendance is append-only, and corrections are appended (not edited), so a
session date's *effective* outcome is its most recent event. All derivations
below therefore reduce the history to the latest event per session date.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.models import (
    SESSION_CONSUMING_STATUSES,
    AttendanceEvent,
    AttendanceStatus,
    Course,
    CourseStatus,
)
from app.services import classes as classes_service
from app.services import persons as persons_service


def get(db: Session, course_id: int) -> Course:
    course = db.scalar(
        select(Course)
        .options(selectinload(Course.client), selectinload(Course.class_type))
        .where(Course.id == course_id)
    )
    if course is None:
        raise NotFoundError("دوره مورد نظر یافت نشد")
    return course


def list_courses(
    db: Session,
    client_id: int | None = None,
    status: CourseStatus | None = None,
) -> list[Course]:
    stmt = (
        select(Course)
        .options(selectinload(Course.client), selectinload(Course.class_type))
        .order_by(Course.created_at.desc())
    )
    if client_id is not None:
        stmt = stmt.where(Course.client_id == client_id)
    if status is not None:
        stmt = stmt.where(Course.status == status)
    return list(db.scalars(stmt))


def effective_status_map(db: Session, course_id: int) -> dict[date, AttendanceStatus]:
    """The latest recorded outcome per session date (corrections win)."""
    events = db.scalars(
        select(AttendanceEvent)
        .where(AttendanceEvent.course_id == course_id)
        .order_by(AttendanceEvent.session_date, AttendanceEvent.id)
    )
    effective: dict[date, AttendanceStatus] = {}
    for event in events:
        effective[event.session_date] = event.status  # later id overwrites → latest wins
    return effective


def consumed_sessions(db: Session, course_id: int) -> int:
    return sum(
        1
        for status in effective_status_map(db, course_id).values()
        if status in SESSION_CONSUMING_STATUSES
    )


def allowed_absence_used(db: Session, course_id: int) -> int:
    return sum(
        1
        for status in effective_status_map(db, course_id).values()
        if status == AttendanceStatus.ABSENT_ALLOWED
    )


def remaining_sessions(db: Session, course: Course) -> int:
    return max(course.sessions_total - consumed_sessions(db, course.id), 0)


def create(
    db: Session,
    client_id: int,
    class_type_id: int,
    sessions_total: int,
    tuition: int = 0,
    gym_fee: int = 0,
    allowed_absence: int = 0,
    start_date: date | None = None,
    travel_declared: bool = False,
    note: str | None = None,
    _carried_credit: int = 0,
) -> Course:
    persons_service.get(db, client_id)
    classes_service.get(db, class_type_id)
    if sessions_total < 1:
        raise ValidationError("تعداد جلسات باید حداقل ۱ باشد")
    if tuition < 0 or gym_fee < 0:
        raise ValidationError("مبلغ نمی‌تواند منفی باشد")
    if allowed_absence < 0:
        raise ValidationError("تعداد غیبت مجاز نمی‌تواند منفی باشد")
    course = Course(
        client_id=client_id,
        class_type_id=class_type_id,
        sessions_total=sessions_total + max(_carried_credit, 0),
        tuition=tuition,
        gym_fee=gym_fee,
        allowed_absence=allowed_absence,
        travel_declared=travel_declared,
        start_date=start_date or date.today(),
        note=note,
    )
    db.add(course)
    db.commit()
    return get(db, course.id)


def set_status(db: Session, course_id: int, status: CourseStatus) -> Course:
    course = get(db, course_id)
    course.status = status
    db.commit()
    db.refresh(course)
    return course


def finish_if_exhausted(db: Session, course_id: int) -> Course:
    """Auto-finish an active course once all paid sessions are consumed."""
    course = get(db, course_id)
    if course.status == CourseStatus.ACTIVE and remaining_sessions(db, course) == 0:
        course.status = CourseStatus.FINISHED
        db.commit()
        db.refresh(course)
    return course


def renew(
    db: Session,
    course_id: int,
    sessions_total: int,
    tuition: int = 0,
    gym_fee: int = 0,
    allowed_absence: int | None = None,
    start_date: date | None = None,
    carry_credit: bool = True,
    note: str | None = None,
) -> Course:
    """Create a NEW course for the same client, carrying eligible unused sessions.

    The previous course is finished (never reset/overwritten); its remaining
    paid sessions roll into the new course as carried credit when `carry_credit`.
    """
    old = get(db, course_id)
    carried = remaining_sessions(db, old) if carry_credit else 0
    if allowed_absence is None:
        allowed_absence = old.allowed_absence
    new_course = create(
        db,
        client_id=old.client_id,
        class_type_id=old.class_type_id,
        sessions_total=sessions_total,
        tuition=tuition,
        gym_fee=gym_fee,
        allowed_absence=allowed_absence,
        start_date=start_date,
        note=note,
        _carried_credit=carried,
    )
    if old.status != CourseStatus.FINISHED:
        old.status = CourseStatus.FINISHED
        db.commit()
    return new_course
