"""Shared message formatters for client (and admin) views."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.copy import texts
from app.core.jalali import format_jalali
from app.models import Course, CourseStatus, PlanAssignment
from app.services import attendance as attendance_service
from app.services import courses as courses_service
from app.services import payments as payments_service
from app.services import schedule as schedule_service


def money(amount: int) -> str:
    return f"{amount:,} {texts.TOMAN}"


def course_status_label(status: CourseStatus) -> str:
    return texts.COURSE_STATUS_LABELS.get(status.value, status.value)


def format_course_detail(
    db: Session,
    course: Course,
    show_history: bool = True,
    show_financial: bool = True,
) -> str:
    consumed = courses_service.consumed_sessions(db, course.id)
    remaining = courses_service.remaining_sessions(db, course)
    # The allowance caps excused absences, so it is what carries the /N — unless
    # it is zero, which means no limit (same rule as the grid header).
    allowed = str(courses_service.allowed_absence_used(db, course.id))
    if course.allowed_absence > 0:
        allowed = f"{allowed}/{course.allowed_absence}"

    lines = [
        f"🏷 {course.class_type.title}",
        f"📌 {texts.LABEL_STATUS}: {course_status_label(course.status)}",
        f"📅 {texts.LABEL_START}: {format_jalali(course.start_date)}",
        f"🗓 {texts.LABEL_TRAINING_DAYS}: {schedule_service.class_schedule_label(course)}",
        f"🎟 {texts.LABEL_TOTAL}: {course.sessions_total}",
        f"✅ {texts.LABEL_CONSUMED}: {consumed}",
        f"💪 {texts.LABEL_REMAINING}: {remaining}",
        f"🆓 {texts.LABEL_ALLOWED_ABSENCE}: {allowed}",
    ]
    # The attendance history is one line per session date (corrections reflected,
    # raw duplicates are not). Both cards now show the colour-coded grid instead,
    # so this text list is opt-in.
    if show_history:
        lines.append("")
        lines.append(f"— {texts.LABEL_ATTENDANCE_HISTORY} —")
        effective = courses_service.effective_status_map(db, course.id)
        if effective:
            for session_date in sorted(effective):
                label = attendance_service.status_label(effective[session_date])
                lines.append(f"{format_jalali(session_date)} — {label}")
        else:
            lines.append(texts.NO_ATTENDANCE_YET)

    # Money is the coach's business — shown on the admin card, hidden from clients.
    if show_financial:
        balance = payments_service.course_balance(db, course)
        lines.append("")
        lines.append(f"— {texts.LABEL_FINANCIAL} —")
        lines.append(f"💰 {texts.LABEL_TUITION}: {money(balance['tuition'])}")
        if balance["gym_fee"]:
            lines.append(f"🏟 {texts.LABEL_GYM_FEE}: {money(balance['gym_fee'])}")
        lines.append(f"💵 {texts.LABEL_PAID}: {money(balance['paid'])}")
        lines.append(f"🧾 {texts.LABEL_OUTSTANDING}: {money(balance['outstanding'])}")
    return "\n".join(lines)


def format_attendance_report(db: Session, course: Course) -> str | None:
    """The per-session attendance record DM'd to a client when a course ends.

    Returns None when nothing was recorded (nothing worth sending).
    """
    effective = courses_service.effective_status_map(db, course.id)
    if not effective:
        return None
    lines = [texts.ATTENDANCE_REPORT_TITLE.format(title=course.class_type.title), ""]
    for session_date in sorted(effective):
        label = attendance_service.status_label(effective[session_date])
        lines.append(f"{format_jalali(session_date)} — {label}")
    lines.append("")
    lines.append(texts.ATTENDANCE_REPORT_FOOTER)
    return "\n".join(lines)


def program_label(assignment: PlanAssignment) -> str:
    """Short label for a program list button."""
    title = assignment.title or assignment.plan_type.title
    return f"{title} | {format_jalali(assignment.created_at)}"


def format_program_caption(assignment: PlanAssignment) -> str:
    lines = [f"📄 {assignment.plan_type.title}"]
    if assignment.title:
        lines.append(assignment.title)
    lines.append(f"تاریخ: {format_jalali(assignment.created_at)}")
    if assignment.coach_note:
        lines.append("")
        lines.append(f"یادداشت مربی: {assignment.coach_note}")
    return "\n".join(lines)
