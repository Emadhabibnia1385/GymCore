"""Attendance recording — history is append-only.

There is deliberately no update or delete function in this module.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.core.jalali import format_jalali
from app.models import AttendanceEvent, AttendanceStatus, CourseStatus
from app.services import courses as courses_service
from app.services import notifications

_STATUS_LABELS = {
    AttendanceStatus.PRESENT: "حاضر ✅",
    AttendanceStatus.ABSENT_ALLOWED: "غیبت مجاز 📝",
    AttendanceStatus.ABSENT_UNAUTHORIZED: "غیبت غیرمجاز ❌",
    AttendanceStatus.COACH_CANCELLED: "کنسلی مربی 🚫",
    AttendanceStatus.HOLIDAY: "تعطیلی 🏖",
}


def status_label(status: AttendanceStatus) -> str:
    return _STATUS_LABELS[status]


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
    notify: bool = True,
) -> AttendanceEvent:
    course = courses_service.get(db, course_id)
    if course.status == CourseStatus.FINISHED:
        raise ValidationError("این دوره به پایان رسیده است")
    if status in {AttendanceStatus.PRESENT, AttendanceStatus.ABSENT_UNAUTHORIZED}:
        if courses_service.remaining_sessions(db, course) <= 0:
            raise ValidationError("جلسه‌ای از این دوره باقی نمانده است")

    event = AttendanceEvent(
        course_id=course_id, session_date=session_date, status=status, note=note
    )
    db.add(event)
    db.commit()

    # Auto-finish once the last paid session is consumed.
    course = courses_service.finish_if_exhausted(db, course_id)

    if notify:
        remaining = courses_service.remaining_sessions(db, course)
        notifications.notify_person(
            db,
            course.client,
            f"یک جلسه‌ی دیگر از مسیرت ثبت شد 🌿\n"
            f"کلاس: {course.class_type.title}\n"
            f"تاریخ: {format_jalali(session_date)}\n"
            f"وضعیت: {status_label(status)}\n"
            f"جلسات باقی‌مانده: {remaining}",
        )
    db.refresh(event)
    return event
