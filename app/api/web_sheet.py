"""The attendance sheet: one month, every student, on one page.

Rows are the days of a Jalali month, columns are the courses running in it, and each cell is
what that course's grid says for that day — the same slots the bot's grid shows, so the sheet
can never disagree with it. Receiving a payment is marked on the day it came in.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.web_deps import require_admin
from app.core import clock
from app.core.jalali import JALALI_MONTHS
from app.db.session import get_db
from app.models import Course, CourseStatus
from app.services import finance as finance_service
from app.services import payments as payments_service
from app.services import schedule as schedule_service

router = APIRouter(prefix="/api/admin", tags=["attendance"], dependencies=[Depends(require_admin)])


class SheetDay(BaseModel):
    iso: str
    day: int
    weekday: str
    friday: bool
    today: bool


class SheetColumn(BaseModel):
    course_id: int
    student: str
    class_title: str
    status: str


class SheetCell(BaseModel):
    status: str | None  # an AttendanceStatus, or None for a session still to come
    session_no: int | None
    paid: bool = False


class Sheet(BaseModel):
    jy: int
    jm: int
    label: str
    prev: tuple[int, int]
    next: tuple[int, int] | None
    days: list[SheetDay]
    columns: list[SheetColumn]
    cells: dict[str, dict[str, SheetCell]]  # course id → day (iso) → cell


@router.get("/attendance/sheet", response_model=Sheet, operation_id="attendance_sheet")
def attendance_sheet(
    year: int | None = Query(default=None, ge=1300, le=1500),
    month: int | None = Query(default=None, ge=1, le=12),
    db: Session = Depends(get_db),
) -> Sheet:
    today = clock.today()
    current = finance_service.month_of(today)
    jy, jm = (year, month) if year and month else current
    first, last = finance_service.jalali_month_bounds(jy, jm)
    days = []
    day = first
    while day <= last:
        weekday = schedule_service.persian_weekday(day)
        days.append(SheetDay(
            iso=day.isoformat(), day=(day - first).days + 1,
            weekday=schedule_service.WEEKDAY_NAMES[weekday], friday=weekday == 6,
            today=day == today,
        ))
        day += timedelta(days=1)

    columns: list[SheetColumn] = []
    cells: dict[str, dict[str, SheetCell]] = {}
    courses = db.scalars(
        select(Course).where(Course.start_date <= last).order_by(Course.client_id, Course.id)
    )
    for course in courses:
        slots = {s.date: s for s in schedule_service.build(db, course) if first <= s.date <= last}
        paid_days = {
            p.paid_at for p in payments_service.list_payments(db, course_id=course.id)
            if p.amount > 0 and first <= p.paid_at <= last
        }
        if not slots and not paid_days:
            continue
        if not slots and course.status != CourseStatus.ACTIVE:
            continue
        columns.append(SheetColumn(
            course_id=course.id, student=course.client.name,
            class_title=course.class_type.title, status=course.status.value,
        ))
        row: dict[str, SheetCell] = {}
        for slot_day in sorted(set(slots) | paid_days):
            slot = slots.get(slot_day)
            row[slot_day.isoformat()] = SheetCell(
                status=slot.status.value if slot and slot.status else None,
                session_no=slot.session_no if slot else None,
                paid=slot_day in paid_days,
            )
        cells[str(course.id)] = row

    prev = finance_service.shift_month(jy, jm, -1)
    following = finance_service.shift_month(jy, jm, 1)
    return Sheet(
        jy=jy, jm=jm, label=f"{JALALI_MONTHS[jm - 1]} {jy}", prev=prev,
        next=following if following <= current else None,
        days=days, columns=columns, cells=cells,
    )
