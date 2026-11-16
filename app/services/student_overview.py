"""One student at a glance: how they attend, since when, and what happened lately.

Derived from the same grids, payments and notes the rest of the panel reads, so it can
never disagree with them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import clock
from app.core.jalali import format_jalali
from app.models import (
    AttendanceEvent,
    AttendanceStatus,
    Course,
    PlanAssignment,
)
from app.services import attendance as attendance_service
from app.services import crm as crm_service
from app.services import payments as payments_service
from app.services import schedule as schedule_service

_ABSENT = (AttendanceStatus.ABSENT_ALLOWED, AttendanceStatus.ABSENT_UNAUTHORIZED)
ACTIVITY_LIMIT = 25


@dataclass
class Stats:
    present: int = 0
    absent_allowed: int = 0
    absent_unauthorized: int = 0
    cancelled: int = 0
    rate: float | None = None  # percent of attended or missed sessions that were attended
    since: str | None = None  # the first course's start, in Jalali
    courses: int = 0
    last_session: str | None = None
    next_session: str | None = None
    average_payment: int = 0
    payment_count: int = 0


@dataclass
class Activity:
    kind: str  # attendance | payment | note | program
    day: date
    title: str
    detail: str | None = None
    amount: int | None = None
    status: str | None = None


@dataclass
class Overview:
    stats: Stats = field(default_factory=Stats)
    activity: list[Activity] = field(default_factory=list)


def _day(stamp: date | datetime) -> date:
    return stamp.date() if isinstance(stamp, datetime) else stamp


def overview(db: Session, person_id: int) -> Overview:
    today = clock.today()
    courses = list(db.scalars(select(Course).where(Course.client_id == person_id)))
    stats = Stats(courses=len(courses))
    if courses:
        stats.since = format_jalali(min(c.start_date for c in courses))
    upcoming: list[date] = []
    last_done: date | None = None
    for course in courses:
        grid = schedule_service.summary(db, course)
        stats.present += grid["present"]
        stats.absent_allowed += grid["absent_allowed"]
        stats.absent_unauthorized += grid["absent_unauthorized"]
        stats.cancelled += grid["cancelled"]
        for slot in grid["slots"]:
            if slot.status is None and slot.date >= today and course.status.value == "ACTIVE":
                upcoming.append(slot.date)
            elif slot.status in (AttendanceStatus.PRESENT, *_ABSENT) and slot.date <= today:
                last_done = max(last_done, slot.date) if last_done else slot.date
    counted = stats.present + stats.absent_allowed + stats.absent_unauthorized
    stats.rate = round(100 * stats.present / counted, 1) if counted else None
    stats.last_session = format_jalali(last_done) if last_done else None
    stats.next_session = format_jalali(min(upcoming)) if upcoming else None

    paid = [p for p in payments_service.list_payments(db, person_id=person_id) if p.amount > 0]
    stats.payment_count = len(paid)
    stats.average_payment = round(sum(p.amount for p in paid) / len(paid)) if paid else 0

    items: list[Activity] = []
    course_ids = [c.id for c in courses]
    titles = {c.id: c.class_type.title for c in courses}
    if course_ids:
        events = db.scalars(
            select(AttendanceEvent).where(AttendanceEvent.course_id.in_(course_ids))
            .order_by(AttendanceEvent.session_date.desc(), AttendanceEvent.id.desc())
            .limit(ACTIVITY_LIMIT)
        )
        seen: set[tuple[int, date]] = set()
        for event in events:  # the latest outcome per session wins
            if (event.course_id, event.session_date) in seen:
                continue
            seen.add((event.course_id, event.session_date))
            items.append(Activity(
                "attendance", event.session_date, attendance_service.status_label(event.status),
                titles.get(event.course_id), status=event.status.value,
            ))
    for payment in payments_service.list_payments(db, person_id=person_id)[:ACTIVITY_LIMIT]:
        items.append(Activity(
            "payment", payment.paid_at, payments_service.kind_label(payment.kind),
            payment.note, amount=payment.amount,
        ))
    for note in crm_service.list_notes(db, person_id, limit=ACTIVITY_LIMIT):
        items.append(Activity("note", _day(note.created_at), note.text[:140]))
    for program in db.scalars(
        select(PlanAssignment).where(PlanAssignment.person_id == person_id)
        .order_by(PlanAssignment.created_at.desc()).limit(ACTIVITY_LIMIT)
    ):
        items.append(Activity(
            "program", _day(program.created_at), program.title or program.plan_type.title,
        ))
    items.sort(key=lambda a: a.day, reverse=True)
    return Overview(stats=stats, activity=items[:ACTIVITY_LIMIT])
