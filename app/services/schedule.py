"""Session grid — the coach's attendance table, derived (never stored).

A course is a list of *slots*, one per training day, rendered in the bots as a
three-cell row: weekday · Jalali date · outcome.

The rules the coach actually uses on paper:

- The grid always ends up holding exactly ``sessions_total`` **consuming**
  slots (✅ حاضر and 🔴 غیبت غیرمجاز burn a paid session).
- 🟡 غیبت مجاز / 🔵 لغو مربی / ⚪ تعطیلی do **not** burn a session, so every one
  of them pushes one extra row onto the end of the grid — the client gets that
  session back on a later date.
- Session numbers count only consuming slots, in date order: جلسه ۱، جلسه ۲، …
- Slots with no recorded outcome yet are «در انتظار».

Dates come from the course's weekly pattern (``Course.weekdays``, Persian
weekday indexes) walking forward from ``start_date``. Off-schedule sessions the
coach records by hand are merged in by date, so the grid never loses history.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    SESSION_CONSUMING_STATUSES,
    AttendanceEvent,
    AttendanceStatus,
    Course,
)

# Persian week: index 0 is شنبه (Saturday), 6 is جمعه (Friday).
WEEKDAY_NAMES = (
    "شنبه",
    "یک‌شنبه",
    "دوشنبه",
    "سه‌شنبه",
    "چهارشنبه",
    "پنج‌شنبه",
    "جمعه",
)
WEEKDAY_SHORT = ("ش", "ی", "د", "س", "چ", "پ", "ج")

# Safety rail for the date walker so a corrupt weekday set can never spin.
_MAX_SCAN_DAYS = 3650


def persian_weekday(value: date) -> int:
    """Python's Monday=0 weekday → Persian شنبه=0 index."""
    return (value.weekday() + 2) % 7


def weekday_name(value: date) -> str:
    return WEEKDAY_NAMES[persian_weekday(value)]


# --- the weekly pattern stored on Course.weekdays ("0,2,4") ---


def parse_weekdays(raw: str | None) -> list[int]:
    days = set()
    for part in (raw or "").split(","):
        part = part.strip()
        if part.isdigit() and 0 <= int(part) <= 6:
            days.add(int(part))
    return sorted(days)


def format_weekdays(days: list[int] | set[int]) -> str:
    return ",".join(str(d) for d in sorted(set(days)) if 0 <= d <= 6)


def weekdays_label(raw: str | None) -> str:
    days = parse_weekdays(raw)
    return "، ".join(WEEKDAY_NAMES[d] for d in days) if days else "—"


# --- per-day class times stored on Course.class_times ("0@20:00,2@18:30") ---


def parse_day_times(raw: str | None) -> dict[int, str]:
    """Weekday index → time label, for the days that have a time set."""
    times: dict[int, str] = {}
    for part in (raw or "").split(","):
        day, _, time = part.strip().partition("@")
        day = day.strip()
        time = time.strip()
        if day.isdigit() and 0 <= int(day) <= 6 and time:
            times[int(day)] = time
    return times


def format_day_times(times: dict[int, str]) -> str:
    """Serialize a weekday→time map back to the stored form (sorted, non-empty)."""
    return ",".join(
        f"{day}@{times[day].strip()}"
        for day in sorted(times)
        if (times.get(day) or "").strip()
    )


def class_schedule_label(course: Course) -> str:
    """Training days with each day's time, e.g. «شنبه ۲۰:۰۰، دوشنبه ۱۸:۳۰».

    Falls back to the single ``class_time`` for older courses, and shows a bare
    weekday when a day has no time yet.
    """
    days = parse_weekdays(course.weekdays)
    if not days:
        return "—"
    times = parse_day_times(getattr(course, "class_times", None))
    fallback = (getattr(course, "class_time", None) or "").strip()
    parts = []
    for day in days:
        time = (times.get(day) or fallback).strip()
        parts.append(f"{WEEKDAY_NAMES[day]} {time}".strip())
    return "، ".join(parts)


def course_weekdays(course: Course) -> list[int]:
    """The course's training days, falling back to the start date's weekday.

    Older courses (created before the weekly pattern existed) have no pattern
    stored; treating them as "same weekday as the start date" keeps their grid
    sensible instead of empty.
    """
    days = parse_weekdays(course.weekdays)
    return days or [persian_weekday(course.start_date)]


def iter_scheduled(start: date, days: list[int] | set[int]):
    """Yield successive training dates from `start` (inclusive)."""
    wanted = {d for d in days if 0 <= d <= 6}
    if not wanted:
        return
    cursor = start
    for _ in range(_MAX_SCAN_DAYS):
        if persian_weekday(cursor) in wanted:
            yield cursor
        cursor += timedelta(days=1)


# --- slots ---


@dataclass(frozen=True)
class Slot:
    """One row of the grid."""

    date: date
    status: AttendanceStatus | None  # None → «در انتظار»
    session_no: int | None  # counter, consuming slots only
    note: str | None
    recorded: bool

    @property
    def weekday(self) -> str:
        return weekday_name(self.date)

    @property
    def consuming(self) -> bool:
        return self.status in SESSION_CONSUMING_STATUSES


def _effective_events(db: Session, course_id: int) -> dict[date, AttendanceEvent]:
    """Latest event per session date (corrections are appended, so latest wins)."""
    events = db.scalars(
        select(AttendanceEvent)
        .where(AttendanceEvent.course_id == course_id)
        .order_by(AttendanceEvent.session_date, AttendanceEvent.id)
    )
    effective: dict[date, AttendanceEvent] = {}
    for event in events:
        effective[event.session_date] = event
    return effective


def build(db: Session, course: Course) -> list[Slot]:
    """The full grid for a course, in date order.

    Recorded sessions show their outcome; every other scheduled date — walking
    the weekly pattern from the start, INCLUDING dates the coach skipped over —
    shows as pending, until the course holds ``sessions_total`` consuming slots.
    Filling from the start (not just after the last recorded date) keeps the
    timeline continuous, so a skipped week never silently disappears.
    """
    effective = _effective_events(db, course.id)
    slots: list[Slot] = []
    consumed = 0
    for session_date in sorted(effective):
        event = effective[session_date]
        session_no = None
        if event.status in SESSION_CONSUMING_STATUSES:
            consumed += 1
            session_no = consumed
        slots.append(
            Slot(
                date=session_date,
                status=event.status,
                session_no=session_no,
                note=event.note,
                recorded=True,
            )
        )

    # Pending rows fill the weekly pattern from the start date, skipping dates
    # already recorded, so gaps in the middle reappear as «در انتظار».
    pending = max(course.sessions_total - consumed, 0)
    added = 0
    for session_date in iter_scheduled(course.start_date, course_weekdays(course)):
        if added >= pending:
            break
        if session_date in effective:
            continue
        slots.append(
            Slot(
                date=session_date,
                status=None,
                session_no=None,
                note=None,
                recorded=False,
            )
        )
        added += 1

    slots.sort(key=lambda slot: slot.date)
    return slots


def find_slot(slots: list[Slot], session_date: date) -> Slot | None:
    for slot in slots:
        if slot.date == session_date:
            return slot
    return None


def next_pending(slots: list[Slot]) -> Slot | None:
    """The first slot still waiting for an outcome — where the coach should land."""
    for slot in slots:
        if not slot.recorded:
            return slot
    return None


def summary(db: Session, course: Course) -> dict:
    """Counters for the grid header (all derived from the same slots)."""
    slots = build(db, course)
    counts = {status: 0 for status in AttendanceStatus}
    for slot in slots:
        if slot.status is not None:
            counts[slot.status] += 1
    consumed = sum(counts[s] for s in SESSION_CONSUMING_STATUSES)
    return {
        "slots": slots,
        "total": course.sessions_total,
        "consumed": consumed,
        "remaining": max(course.sessions_total - consumed, 0),
        "present": counts[AttendanceStatus.PRESENT],
        "absent_allowed": counts[AttendanceStatus.ABSENT_ALLOWED],
        "absent_unauthorized": counts[AttendanceStatus.ABSENT_UNAUTHORIZED],
        "cancelled": counts[AttendanceStatus.COACH_CANCELLED],
        "holiday": counts[AttendanceStatus.HOLIDAY],
    }
