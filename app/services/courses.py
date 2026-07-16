"""Course management.

Core rule: remaining sessions are ALWAYS computed from attendance history,
never stored. Only PRESENT and ABSENT_UNAUTHORIZED consume sessions.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.models import (
    SESSION_CONSUMING_STATUSES,
    AttendanceEvent,
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


def consumed_sessions(db: Session, course_id: int) -> int:
    """Count attendance events that burn a paid session."""
    return (
        db.scalar(
            select(func.count(AttendanceEvent.id)).where(
                AttendanceEvent.course_id == course_id,
                AttendanceEvent.status.in_(SESSION_CONSUMING_STATUSES),
            )
        )
        or 0
    )


def remaining_sessions(db: Session, course: Course) -> int:
    return max(course.sessions_total - consumed_sessions(db, course.id), 0)


def create(
    db: Session,
    client_id: int,
    class_type_id: int,
    sessions_total: int,
    tuition: int,
    gym_fee: int,
    start_date: date,
    note: str | None = None,
) -> Course:
    # Validate references exist and inputs make sense.
    persons_service.get(db, client_id)
    classes_service.get(db, class_type_id)
    if sessions_total < 1:
        raise ValidationError("تعداد جلسات باید حداقل ۱ باشد")
    if tuition < 0 or gym_fee < 0:
        raise ValidationError("مبلغ نمی‌تواند منفی باشد")
    course = Course(
        client_id=client_id,
        class_type_id=class_type_id,
        sessions_total=sessions_total,
        tuition=tuition,
        gym_fee=gym_fee,
        start_date=start_date,
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
    """Auto-finish a course once all paid sessions are consumed."""
    course = get(db, course_id)
    if (
        course.status == CourseStatus.ACTIVE
        and remaining_sessions(db, course) == 0
    ):
        course.status = CourseStatus.FINISHED
        db.commit()
        db.refresh(course)
    return course
