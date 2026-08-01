"""Course management.

Core rule: remaining sessions are ALWAYS computed from attendance history,
never stored. Only PRESENT and ABSENT_UNAUTHORIZED consume sessions.

Attendance is append-only, and corrections are appended (not edited), so a
session date's *effective* outcome is its most recent event. All derivations
below therefore reduce the history to the latest event per session date.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Select, select
from sqlalchemy import delete as sa_delete
from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.models import (
    SESSION_CONSUMING_STATUSES,
    AttendanceEvent,
    AttendanceStatus,
    Course,
    CourseStatus,
    Payment,
    PaymentKind,
)
from app.services import classes as classes_service
from app.services import persons as persons_service
from app.services import schedule


def get(db: Session, course_id: int) -> Course:
    course = db.scalar(
        select(Course)
        .options(selectinload(Course.client), selectinload(Course.class_type))
        .where(Course.id == course_id)
    )
    if course is None:
        raise NotFoundError("دوره مورد نظر یافت نشد")
    return course


def list_stmt(
    client_id: int | None = None,
    status: CourseStatus | None = None,
) -> Select:
    """Select for a course list — also feeds the paginated admin pickers."""
    stmt = (
        select(Course)
        .options(selectinload(Course.client), selectinload(Course.class_type))
        .order_by(Course.created_at.desc())
    )
    if client_id is not None:
        stmt = stmt.where(Course.client_id == client_id)
    if status is not None:
        stmt = stmt.where(Course.status == status)
    return stmt


def list_courses(
    db: Session,
    client_id: int | None = None,
    status: CourseStatus | None = None,
) -> list[Course]:
    return list(db.scalars(list_stmt(client_id, status)))


def active_course(db: Session, client_id: int) -> Course | None:
    """The client's current course — what the student hub opens onto."""
    return db.scalar(list_stmt(client_id, CourseStatus.ACTIVE).limit(1))


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


def per_session_cost(course: Course) -> int:
    """The course's price for a single session: (tuition + gym fee) ÷ sessions."""
    if course.sessions_total <= 0:
        return 0
    return round(((course.tuition or 0) + (course.gym_fee or 0)) / course.sessions_total)


def coach_cancelled_count(db: Session, course_id: int) -> int:
    """How many of the course's sessions the coach cancelled (effective outcome)."""
    return sum(
        1
        for status in effective_status_map(db, course_id).values()
        if status == AttendanceStatus.COACH_CANCELLED
    )


def coach_cancel_credit(db: Session, course: Course) -> int:
    """Money owed back for coach-cancelled sessions — one session's cost each."""
    return coach_cancelled_count(db, course.id) * per_session_cost(course)


def create(
    db: Session,
    client_id: int,
    class_type_id: int,
    sessions_total: int,
    tuition: int = 0,
    gym_fee: int = 0,
    allowed_absence: int = 0,
    start_date: date | None = None,
    weekdays: str | None = None,
    class_time: str | None = None,
    class_times: str | None = None,
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
        weekdays=schedule.format_weekdays(schedule.parse_weekdays(weekdays)) or None,
        class_time=(class_time or "").strip() or None,
        class_times=schedule.format_day_times(schedule.parse_day_times(class_times)) or None,
        note=note,
    )
    db.add(course)
    db.commit()
    return get(db, course.id)


def set_weekdays(db: Session, course_id: int, weekdays: str | None) -> Course:
    """Change the weekly training pattern (reshapes the derived grid only)."""
    course = get(db, course_id)
    course.weekdays = schedule.format_weekdays(schedule.parse_weekdays(weekdays)) or None
    db.commit()
    db.refresh(course)
    return course


def set_class_times(db: Session, course_id: int, class_times: str | None) -> Course:
    """Change the per-day class times (display only; doesn't touch the grid)."""
    course = get(db, course_id)
    course.class_times = schedule.format_day_times(schedule.parse_day_times(class_times)) or None
    db.commit()
    db.refresh(course)
    return course


def set_status(db: Session, course_id: int, status: CourseStatus) -> Course:
    course = get(db, course_id)
    course.status = status
    db.commit()
    db.refresh(course)
    return course


def delete(db: Session, course_id: int) -> int:
    """Delete a course and its session history.

    Attendance events (course-scoped) are removed; payments are kept as
    person-level records (their course link is cleared) so money history is
    never lost. Returns the owning client's id.
    """
    course = get(db, course_id)
    client_id = course.client_id
    db.execute(sa_delete(AttendanceEvent).where(AttendanceEvent.course_id == course_id))
    db.execute(sa_update(Payment).where(Payment.course_id == course_id).values(course_id=None))
    db.delete(course)
    db.commit()
    return client_id


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
    weekdays: str | None = None,
    class_time: str | None = None,
    class_times: str | None = None,
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
        weekdays=weekdays if weekdays is not None else old.weekdays,
        class_time=class_time if class_time is not None else old.class_time,
        class_times=class_times if class_times is not None else old.class_times,
        note=note,
        _carried_credit=carried,
    )
    # Coach-cancelled sessions come back as time (carried above) AND as money:
    # one session's cost each is credited onto the new course.
    credit = coach_cancel_credit(db, old)
    if credit > 0:
        from app.services import payments as payments_service

        payments_service.record(
            db,
            person_id=old.client_id,
            amount=credit,
            kind=PaymentKind.OTHER,
            paid_at=date.today(),
            course_id=new_course.id,
            note="اعتبار جلسات لغوشدهٔ مربی از دورهٔ قبل",
            notify=False,
        )
    if old.status != CourseStatus.FINISHED:
        old.status = CourseStatus.FINISHED
        db.commit()
    return new_course
