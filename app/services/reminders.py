"""Automated client reminders.

The reminder worker (app/jobs/reminders.py) calls `scan_and_send` on a fixed
interval. All the decision logic lives here so it can be unit-tested offline
with `notifications.enabled = False`.

Two reminder kinds are supported today:

- LOW_SESSIONS:    an active course whose remaining sessions dropped to/below
                   `reminder_low_session_threshold`.
- COURSE_INACTIVE: an active course with no attendance for
                   `reminder_inactive_days` days (measured from the last
                   session, or the course start date if none yet).

De-duplication: before sending, we look at the most recent ReminderLog row for
that (course, kind) and skip if it is newer than `reminder_resend_days`. Every
send appends a ReminderLog row (append-only) as both an audit trail and the
dedup marker.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    AttendanceEvent,
    Course,
    CourseStatus,
    ReminderKind,
    ReminderLog,
)
from app.services import courses as courses_service
from app.services import notifications

logger = logging.getLogger(__name__)


def _last_activity(db: Session, course: Course) -> date:
    """Date of the most recent recorded session, or the course start date."""
    last_session = db.scalar(
        select(func.max(AttendanceEvent.session_date)).where(
            AttendanceEvent.course_id == course.id
        )
    )
    return last_session or course.start_date


def _recently_sent(
    db: Session, course_id: int, kind: ReminderKind, today: date, resend_days: int
) -> bool:
    """True if this reminder kind was already sent for this course recently."""
    last = db.scalar(
        select(ReminderLog)
        .where(ReminderLog.course_id == course_id, ReminderLog.kind == kind)
        .order_by(ReminderLog.sent_at.desc())
        .limit(1)
    )
    if last is None or last.sent_at is None:
        return False
    return (today - last.sent_at.date()).days < resend_days


def _low_sessions_text(course: Course, remaining: int) -> str:
    return (
        "یادِ تو هستیم ⏰\n"
        f"از دوره‌ی «{course.class_type.title}» تنها {remaining} جلسه برایت باقی مانده.\n"
        "برای تمدید و ادامه‌ی مسیر با مربی هماهنگ کن."
    )


def _inactive_text(course: Course, inactive_days: int) -> str:
    return (
        "جایت این روزها خالی‌ست 🌿\n"
        f"مدتی است در دوره‌ی «{course.class_type.title}» جلسه‌ای ثبت نشده "
        f"({inactive_days} روز)؛ منتظر بازگشتت هستیم."
    )


def _record_and_notify(
    db: Session,
    course: Course,
    kind: ReminderKind,
    text: str,
    detail: str,
    now: datetime,
) -> ReminderLog:
    """Append the ReminderLog row, then push the message (fire-and-forget)."""
    log = ReminderLog(course_id=course.id, kind=kind, detail=detail, sent_at=now)
    db.add(log)
    db.commit()
    db.refresh(log)
    notifications.notify_person(db, course.client, text)
    return log


def scan_and_send(db: Session, now: datetime | None = None) -> list[ReminderLog]:
    """Scan active courses and send any due reminders.

    Returns the ReminderLog rows created this run (empty if nothing was due).
    `now` is injectable for deterministic tests; it defaults to the current
    UTC time.
    """
    settings = get_settings()
    now = now or datetime.now(UTC)
    today = now.date()
    threshold = settings.reminder_low_session_threshold
    inactive_days_limit = settings.reminder_inactive_days
    resend_days = settings.reminder_resend_days

    created: list[ReminderLog] = []
    for course in courses_service.list_courses(db, status=CourseStatus.ACTIVE):
        remaining = courses_service.remaining_sessions(db, course)

        # Low remaining sessions.
        if 0 < remaining <= threshold and not _recently_sent(
            db, course.id, ReminderKind.LOW_SESSIONS, today, resend_days
        ):
            created.append(
                _record_and_notify(
                    db,
                    course,
                    ReminderKind.LOW_SESSIONS,
                    _low_sessions_text(course, remaining),
                    detail=f"remaining={remaining}",
                    now=now,
                )
            )

        # Inactivity.
        inactive_days = (today - _last_activity(db, course)).days
        if inactive_days >= inactive_days_limit and not _recently_sent(
            db, course.id, ReminderKind.COURSE_INACTIVE, today, resend_days
        ):
            created.append(
                _record_and_notify(
                    db,
                    course,
                    ReminderKind.COURSE_INACTIVE,
                    _inactive_text(course, inactive_days),
                    detail=f"inactive_days={inactive_days}",
                    now=now,
                )
            )

    if created:
        logger.info("Reminders sent: %d", len(created))
    return created
