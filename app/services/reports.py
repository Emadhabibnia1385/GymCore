"""The coach's reports: one year of the gym's life in a single read.

Everything is derived from the same tables the bot and the dashboard use — payments,
expenses, courses and the attendance log — so the report can never disagree with them.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.copy import finance_texts as F
from app.core import clock
from app.core.jalali import JALALI_MONTHS, format_jalali
from app.models import (
    AttendanceEvent,
    AttendanceStatus,
    ClassType,
    Course,
    CourseStatus,
    Expense,
    Payment,
    Person,
    Role,
)
from app.services import finance as finance_service
from app.services import payments as payments_service
from app.services import schedule as schedule_service

ENDING_SOON = 2  # sessions left at or under which a course is about to end
_WEEKS = 8
_ABSENT = (AttendanceStatus.ABSENT_ALLOWED, AttendanceStatus.ABSENT_UNAUTHORIZED)


def _share(part: int, whole: int) -> float:
    return round(100 * part / whole, 1) if whole else 0.0


def _months(db: Session, jy: int) -> list[dict]:
    first, _ = finance_service.jalali_month_bounds(jy, 1)
    _, last = finance_service.jalali_month_bounds(jy, 12)
    new_students = [0] * 12
    for (stamp,) in db.execute(
        select(Person.created_at).where(Person.role == Role.CLIENT)
    ):
        day = stamp.date() if stamp else None
        if day and first <= day <= last:
            new_students[finance_service.month_of(day)[1] - 1] += 1
    new_courses = [0] * 12
    for (start,) in db.execute(
        select(Course.start_date).where(Course.start_date >= first, Course.start_date <= last)
    ):
        new_courses[finance_service.month_of(start)[1] - 1] += 1
    before = finance_service.year_overview(db, jy - 1)
    return [
        {
            "month": row.jm, "label": JALALI_MONTHS[row.jm - 1], "income": row.income,
            "expenses": row.expenses, "net": row.net, "previous_income": before[row.jm - 1].income,
            "new_students": new_students[row.jm - 1], "new_courses": new_courses[row.jm - 1],
        }
        for row in finance_service.year_overview(db, jy)
    ]


def _year_lines(db: Session, jy: int) -> tuple[list[dict], list[dict]]:
    first, _ = finance_service.jalali_month_bounds(jy, 1)
    _, last = finance_service.jalali_month_bounds(jy, 12)
    income = db.execute(
        select(Payment.kind, func.sum(Payment.amount))
        .where(Payment.paid_at >= first, Payment.paid_at <= last).group_by(Payment.kind)
    )
    spent = db.execute(
        select(Expense.category, func.sum(Expense.amount))
        .where(Expense.spent_at >= first, Expense.spent_at <= last).group_by(Expense.category)
    )
    return (
        [{"key": k.value, "label": payments_service.kind_label(k), "amount": int(v or 0)}
         for k, v in income],
        [{"key": c.value, "label": F.CATEGORY_LABELS.get(c, c.value), "amount": int(v or 0)}
         for c, v in spent],
    )


def _attendance(db: Session, today: date) -> tuple[dict, list[dict]]:
    since = today - timedelta(days=30)
    counts = dict(db.execute(
        select(AttendanceEvent.status, func.count())
        .where(AttendanceEvent.session_date >= since, AttendanceEvent.session_date <= today)
        .group_by(AttendanceEvent.status)
    ).all())
    present = counts.get(AttendanceStatus.PRESENT, 0)
    absent = sum(counts.get(s, 0) for s in _ABSENT)
    month = {
        "present": present,
        "absent_allowed": counts.get(AttendanceStatus.ABSENT_ALLOWED, 0),
        "absent_unauthorized": counts.get(AttendanceStatus.ABSENT_UNAUTHORIZED, 0),
        "cancelled": counts.get(AttendanceStatus.COACH_CANCELLED, 0),
        "holiday": counts.get(AttendanceStatus.HOLIDAY, 0),
        "rate": _share(present, present + absent),
    }
    # The Jalali week starts on Saturday; eight of them, the newest last.
    this_week = today - timedelta(days=schedule_service.persian_weekday(today))
    starts = [this_week - timedelta(weeks=n) for n in range(_WEEKS - 1, -1, -1)]
    weeks = {start: {"present": 0, "absent": 0} for start in starts}
    for day, status in db.execute(
        select(AttendanceEvent.session_date, AttendanceEvent.status)
        .where(AttendanceEvent.session_date >= starts[0], AttendanceEvent.session_date <= today)
    ):
        start = day - timedelta(days=schedule_service.persian_weekday(day))
        if start in weeks and status == AttendanceStatus.PRESENT:
            weeks[start]["present"] += 1
        elif start in weeks and status in _ABSENT:
            weeks[start]["absent"] += 1
    return month, [
        {"label": format_jalali(start)[5:], **weeks[start]} for start in starts
    ]


def build(db: Session, jy: int | None = None) -> dict:
    today = clock.today()
    current_jy, current_jm = finance_service.month_of(today)
    jy = jy or current_jy
    months = _months(db, jy)

    this_month = months[current_jm - 1] if jy == current_jy else None
    last_month = months[current_jm - 2] if jy == current_jy and current_jm > 1 else None

    courses = list(db.scalars(select(Course)))
    status_count = defaultdict(int)
    ending: list[dict] = []
    by_class: dict[int, dict] = {}
    class_names = {c.id: c.title for c in db.scalars(select(ClassType))}
    for course in courses:
        status_count[course.status] += 1
        if course.status != CourseStatus.ACTIVE:
            continue
        row = by_class.setdefault(course.class_type_id, {
            "title": class_names.get(course.class_type_id, "—"), "active_courses": 0, "income": 0,
        })
        row["active_courses"] += 1
        remaining = schedule_service.summary(db, course)["remaining"]
        if remaining <= ENDING_SOON:
            ending.append({
                "course_id": course.id, "student": course.client.name,
                "class_title": class_names.get(course.class_type_id, "—"), "remaining": remaining,
            })
    first, _ = finance_service.jalali_month_bounds(jy, 1)
    _, last = finance_service.jalali_month_bounds(jy, 12)
    for class_type_id, total in db.execute(
        select(Course.class_type_id, func.sum(Payment.amount))
        .join(Course, Course.id == Payment.course_id)
        .where(Payment.paid_at >= first, Payment.paid_at <= last)
        .group_by(Course.class_type_id)
    ):
        by_class.setdefault(class_type_id, {
            "title": class_names.get(class_type_id, "—"), "active_courses": 0, "income": 0,
        })["income"] = int(total or 0)

    income_lines, expense_lines = _year_lines(db, jy)
    attendance, weeks = _attendance(db, today)
    owing = payments_service.outstanding_courses(db)
    paid_rows = db.scalar(
        select(func.count()).select_from(Payment)
        .where(Payment.paid_at >= first, Payment.paid_at <= last, Payment.amount > 0)
    ) or 0
    income_year = sum(m["income"] for m in months)
    spent_year = sum(m["expenses"] for m in months)

    return {
        "year": jy,
        "kpis": {
            "students": db.scalar(select(func.count()).select_from(Person).where(
                Person.role == Role.CLIENT, Person.is_active.is_(True))) or 0,
            "courses_active": status_count[CourseStatus.ACTIVE],
            "courses_finished": status_count[CourseStatus.FINISHED],
            "courses_paused": status_count[CourseStatus.PAUSED],
            "ending_soon": len(ending),
            "income_year": income_year, "expenses_year": spent_year,
            "net_year": income_year - spent_year,
            "average_payment": round(income_year / paid_rows) if paid_rows else 0,
            "owing_total": sum(amount for _, amount in owing), "owing_count": len(owing),
            "income_this_month": this_month["income"] if this_month else None,
            "income_last_month": last_month["income"] if last_month else None,
            "expenses_this_month": this_month["expenses"] if this_month else None,
            "expenses_last_month": last_month["expenses"] if last_month else None,
        },
        "months": months,
        "attendance": attendance,
        "weeks": weeks,
        "classes": sorted(by_class.values(), key=lambda r: (-r["income"], -r["active_courses"])),
        "income_by_kind": income_lines,
        "expenses_by_category": expense_lines,
        "debtors": [
            {"course_id": c.id, "student": c.client.name,
             "class_title": class_names.get(c.class_type_id, "—"), "amount": amount}
            for c, amount in owing[:10]
        ],
        "ending_soon": sorted(ending, key=lambda r: r["remaining"])[:10],
    }
