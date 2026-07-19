"""Attendance recording — history is APPEND-ONLY.

There is deliberately no update or delete. A mistake is fixed with `correct`,
which appends a new event for the same session date; the latest event is the
effective outcome (see services/courses.py::effective_status_map).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.jalali import format_jalali
from app.models import (
    SESSION_CONSUMING_STATUSES,
    AttendanceEvent,
    AttendanceStatus,
    CourseStatus,
)
from app.models.setting import KEY_NOTIFY_ON_ATTENDANCE
from app.services import courses as courses_service
from app.services import notifications
from app.services import settings as settings_service

# Persian labels exactly per the product spec.
_STATUS_LABELS = {
    AttendanceStatus.PRESENT: "✅ حاضر",
    AttendanceStatus.ABSENT_ALLOWED: "🟡 غیبت مجاز",
    AttendanceStatus.ABSENT_UNAUTHORIZED: "🔴 غیبت غیرمجاز",
    AttendanceStatus.COACH_CANCELLED: "🔵 لغو توسط مربی",
    AttendanceStatus.HOLIDAY: "⚪ تعطیلی",
}


def status_label(status: AttendanceStatus) -> str:
    return _STATUS_LABELS[status]


def all_statuses() -> list[AttendanceStatus]:
    return list(_STATUS_LABELS)


def list_for_course(db: Session, course_id: int) -> list[AttendanceEvent]:
    return list(
        db.scalars(
            select(AttendanceEvent)
            .where(AttendanceEvent.course_id == course_id)
            .order_by(AttendanceEvent.session_date, AttendanceEvent.id)
        )
    )


def record(
    db: Session,
    course_id: int,
    session_date: date,
    status: AttendanceStatus,
    note: str | None = None,
    created_by: str | None = None,
    notify: bool = True,
) -> AttendanceEvent:
    course = courses_service.get(db, course_id)
    if course.status == CourseStatus.FINISHED:
        raise ValidationError("این دوره به پایان رسیده است")

    # Block over-consumption, but allow a correction on a date that already
    # consumed a session (it replaces, so the net is unchanged).
    if status in {AttendanceStatus.PRESENT, AttendanceStatus.ABSENT_UNAUTHORIZED}:
        effective = courses_service.effective_status_map(db, course_id)
        already_consuming = effective.get(session_date) in SESSION_CONSUMING_STATUSES
        if not already_consuming and courses_service.remaining_sessions(db, course) <= 0:
            raise ValidationError("جلسه‌ای از این دوره باقی نمانده است")

    was_active = course.status == CourseStatus.ACTIVE

    event = AttendanceEvent(
        course_id=course_id,
        session_date=session_date,
        status=status,
        note=note,
        created_by=created_by,
    )
    db.add(event)
    db.commit()

    # Auto-finish once the last paid session is consumed.
    course = courses_service.finish_if_exhausted(db, course_id)
    if was_active and course.status == CourseStatus.FINISHED:
        _queue_course_ending(db, course)

    if notify and settings_service.get_bool(db, KEY_NOTIFY_ON_ATTENDANCE, True):
        remaining = courses_service.remaining_sessions(db, course)
        notifications.notify_person(
            db,
            course.client,
            "یک جلسه‌ی دیگر از مسیرت ثبت شد 🟢\n"
            f"کلاس: {course.class_type.title}\n"
            f"تاریخ: {format_jalali(session_date)}\n"
            f"وضعیت: {status_label(status)}\n"
            f"جلسات باقی‌مانده: {remaining}",
        )
    db.refresh(event)
    return event


def _queue_course_ending(db: Session, course) -> None:
    """Queue a one-time course-ending notification (idempotent per course)."""
    from app.models import NotificationKind
    from app.notifications import service as notify_service

    notify_service.queue(
        db,
        course.client_id,
        NotificationKind.COURSE_ENDING,
        f"دورهٔ «{course.class_type.title}» به پایان رسید 🟢\nبرای تمدید با مربی هماهنگ کن.",
        idempotency_key=f"ending:{course.id}",
    )


def correct(
    db: Session,
    course_id: int,
    session_date: date,
    status: AttendanceStatus,
    note: str | None = None,
    created_by: str | None = None,
    notify: bool = False,
) -> AttendanceEvent:
    """Append a correcting event for a session date (audit history preserved)."""
    correction_note = note or "اصلاح ثبت حضور"
    return record(
        db,
        course_id=course_id,
        session_date=session_date,
        status=status,
        note=correction_note,
        created_by=created_by,
        notify=notify,
    )
