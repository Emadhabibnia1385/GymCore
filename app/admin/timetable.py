"""Admin section: the weekly timetable — each day of the week and its classes.

Built from the active courses' weekly patterns (services/schedule.py), so it
always matches the session grids and nothing about it is stored. The week is a
text screen, short enough to screenshot; tapping a day opens that day as a
table — time · student · class — whose rows open the student.
"""

from __future__ import annotations

from app.admin import common
from app.admin.common import AdminReq
from app.bots.common import grid
from app.copy import admin_texts as A
from app.services import schedule as schedule_service

# A message caps at 4096 characters; past this the week lists per-day counts.
_MAX_WEEK_CHARS = 3500


def handle_callback(req: AdminReq, args: str) -> None:
    action, _, rest = (args or "").partition(":")
    if action == "day" and rest.isdigit() and int(rest) < len(schedule_service.WEEKDAY_NAMES):
        _day(req, int(rest))
    else:
        _week(req)


def handle_message(req: AdminReq, message: dict, substep: str, state) -> None:
    common.clear(req)  # nothing here asks for typed input
    _week(req)


def _line(entry: schedule_service.TimetableEntry) -> str:
    time = entry.time or A.TIMETABLE_NO_TIME
    return f"{time} — {entry.course.client.name} ({entry.course.class_type.title})"


def _week(req: AdminReq) -> None:
    """The whole week: every day, and under it that day's classes in time order."""
    week = schedule_service.weekly_timetable(req.db)
    names = schedule_service.WEEKDAY_NAMES
    if not any(week.values()):
        body = f"{A.TIMETABLE_TITLE}\n\n{A.TIMETABLE_EMPTY}"
    else:
        sections = []
        for day, name in enumerate(names):
            lines = [_line(entry) for entry in week[day]] or [A.TIMETABLE_DAY_EMPTY]
            sections.append("\n".join([f"▪️ {name}", *lines]))
        body = f"{A.TIMETABLE_TITLE}\n\n" + "\n\n".join(sections)
        if len(body) > _MAX_WEEK_CHARS:
            counts = [
                f"▪️ {name}: {A.TIMETABLE_COUNT.format(n=len(week[day]))}"
                for day, name in enumerate(names)
            ]
            body = f"{A.TIMETABLE_TITLE}\n\n" + "\n".join(counts)
        body = f"{body}\n\n{A.TIMETABLE_HINT}"
    days = [
        common.button(f"{name} ({len(week[day])})", "week", "day", day)
        for day, name in enumerate(names)
    ]
    common.render(req, body, common.with_back([days[:4], days[4:]]))


def _day(req: AdminReq, day: int) -> None:
    """One day as a table — time · student · class; tapping a row opens the student."""
    entries = schedule_service.weekly_timetable(req.db)[day]
    shown = entries[: grid.MAX_ROWS_PER_SCREEN]
    rows = []
    for entry in shown:
        student = entry.course.client_id
        rows.append([
            common.button(entry.time or A.TIMETABLE_NO_TIME, "students", "view", student),
            common.button(entry.course.client.name, "students", "view", student),
            common.button(entry.course.class_type.title, "students", "view", student),
        ])
    title = A.TIMETABLE_DAY_TITLE.format(day=schedule_service.WEEKDAY_NAMES[day])
    if not entries:
        body = f"{title}\n\n{A.TIMETABLE_DAY_EMPTY}"
    elif len(entries) > len(shown):
        note = A.TIMETABLE_DAY_TRUNCATED.format(shown=len(shown), total=len(entries))
        body = f"{title}\n\n{note}"
    else:
        body = f"{title}\n\n{A.TIMETABLE_DAY_HINT}"
    common.render(req, body, common.with_back(rows, ("week",)))
