"""The session-grid screen: three glass buttons per row — weekday · date · outcome.

This is the coach's paper attendance table, rendered as an inline keyboard and
shared by both audiences:

- admin: every cell in a row carries the same callback, so tapping anywhere on
  the row opens that session's outcome picker;
- client: the same layout, inert cells (read-only).

The rows themselves come from :mod:`app.services.schedule`; this module only
turns slots into labels, pages and buttons.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from app.bots.common import callbacks as cb
from app.copy import texts
from app.core.jalali import format_jalali, format_jalali_short
from app.models import AttendanceStatus, Course
from app.services import courses as courses_service
from app.services import payments as payments_service
from app.services import schedule

ROWS_PER_PAGE = 8

# Compact status codes for callback data (Telegram caps callback_data at 64 bytes).
STATUS_CODES: dict[str, AttendanceStatus] = {
    "P": AttendanceStatus.PRESENT,
    "U": AttendanceStatus.ABSENT_UNAUTHORIZED,
    "A": AttendanceStatus.ABSENT_ALLOWED,
    "C": AttendanceStatus.COACH_CANCELLED,
    "H": AttendanceStatus.HOLIDAY,
}
CODE_BY_STATUS = {status: code for code, status in STATUS_CODES.items()}

# The three outcomes the coach uses on almost every session, then the two
# scheduling ones. Order drives the outcome-picker layout.
PRIMARY_STATUSES = (
    AttendanceStatus.PRESENT,
    AttendanceStatus.ABSENT_UNAUTHORIZED,
    AttendanceStatus.ABSENT_ALLOWED,
)
SECONDARY_STATUSES = (
    AttendanceStatus.COACH_CANCELLED,
    AttendanceStatus.HOLIDAY,
)

# Short labels for the grid's third cell (long ones would be truncated).
_CELL_LABELS = {
    AttendanceStatus.PRESENT: "✅ جلسه {n}",
    AttendanceStatus.ABSENT_UNAUTHORIZED: "🔴 غایب {n}",
    AttendanceStatus.ABSENT_ALLOWED: "🟡 غیبت مجاز",
    AttendanceStatus.COACH_CANCELLED: "🔵 لغو مربی",
    AttendanceStatus.HOLIDAY: "⚪ تعطیلی",
}
PENDING_CELL = "⏳ در انتظار"

# Outcome-picker labels — short enough for three buttons in one row, and worded
# the way the coach says them: حاضر / غیبت / مجاز.
PICKER_LABELS = {
    AttendanceStatus.PRESENT: "✅ حاضر",
    AttendanceStatus.ABSENT_UNAUTHORIZED: "🔴 غیبت",
    AttendanceStatus.ABSENT_ALLOWED: "🟡 مجاز",
    AttendanceStatus.COACH_CANCELLED: "🔵 لغو مربی",
    AttendanceStatus.HOLIDAY: "⚪ تعطیلی",
}


# --- date <-> callback token ---


def date_token(value: date) -> str:
    return value.strftime("%Y%m%d")


def parse_date_token(token: str) -> date | None:
    """Parse a `YYYYMMDD` callback token; None on anything malformed (tamper-safe)."""
    if not (token or "").isdigit() or len(token) != 8:
        return None
    try:
        return date(int(token[:4]), int(token[4:6]), int(token[6:]))
    except ValueError:
        return None


# --- cells ---


def status_cell(slot: schedule.Slot) -> str:
    if slot.status is None:
        return PENDING_CELL
    return _CELL_LABELS[slot.status].format(n=slot.session_no or "")


# --- paging ---


def page_count(slots: list) -> int:
    return max((len(slots) + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE, 1)


def page_of(slots: list, session_date: date) -> int:
    for index, slot in enumerate(slots):
        if slot.date == session_date:
            return index // ROWS_PER_PAGE + 1
    return 1


def default_page(slots: list) -> int:
    """Land the coach on the page holding the next unrecorded session."""
    pending = schedule.next_pending(slots)
    return page_of(slots, pending.date) if pending else page_count(slots)


def page_slice(slots: list, page: int) -> tuple[list, int, int]:
    pages = page_count(slots)
    page = min(max(page, 1), pages)
    start = (page - 1) * ROWS_PER_PAGE
    return slots[start : start + ROWS_PER_PAGE], page, pages


# --- rows ---


def rows(slots: list, callback_for) -> list[list[dict]]:
    """Build the three-cell rows. `callback_for(slot)` returns the row's callback_data."""
    built = []
    for slot in slots:
        data = callback_for(slot)
        built.append([
            {"text": slot.weekday, "callback_data": data},
            {"text": format_jalali_short(slot.date), "callback_data": data},
            {"text": status_cell(slot), "callback_data": data},
        ])
    return built


def client_rows(slots: list) -> list[list[dict]]:
    """Read-only rows for the client view — every cell is inert."""
    return rows(slots, lambda _slot: cb.NOOP)


# --- header ---


def header(db: Session, course: Course, page: int, pages: int, *, for_admin: bool) -> str:
    """The text above the grid: who/what, the weekly pattern and the counters."""
    stats = schedule.summary(db, course)
    lines = [texts.GRID_TITLE, f"🏷 {course.class_type.title}"]
    if for_admin:
        lines.append(f"👤 {course.client.name}")
    lines.append(f"🗓 {texts.LABEL_TRAINING_DAYS}: {schedule.weekdays_label(course.weekdays)}")
    lines.append(f"▫️ {texts.LABEL_START}: {format_jalali(course.start_date)}")
    lines.append("")
    lines.append(
        f"🟢 {texts.LABEL_CONSUMED}: {stats['consumed']}/{stats['total']}"
        f" · {texts.LABEL_REMAINING}: {stats['remaining']}"
    )
    lines.append(
        f"🟡 {texts.LABEL_ALLOWED_ABSENCE}: {stats['absent_allowed']}/{course.allowed_absence}"
        f" · 🔴 {texts.LABEL_UNAUTHORIZED}: {stats['absent_unauthorized']}"
    )
    if for_admin:
        balance = payments_service.course_balance(db, course)
        lines.append(
            f"💳 {texts.LABEL_OUTSTANDING}: {balance['outstanding']:,} {texts.TOMAN}"
        )
    if pages > 1:
        lines.append("")
        lines.append(texts.GRID_PAGE.format(page=page, pages=pages))
    return "\n".join(lines)


def course_button_label(db: Session, course: Course, with_name: bool = False) -> str:
    """Label for a course in a picker list: status, class, and session progress."""
    from app.bots.common import formatting

    consumed = courses_service.consumed_sessions(db, course.id)
    prefix = f"{course.client.name} — " if with_name else ""
    return (
        f"{formatting.course_status_label(course.status)} {prefix}"
        f"{course.class_type.title} · {consumed}/{course.sessions_total}"
    )
