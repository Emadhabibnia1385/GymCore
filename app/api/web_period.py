"""Money over any period: a month, a whole year, the last N days, or from one date to another.

One answer for all of them — totals by kind and category, the expense list, a series for the
chart, and the same figures for the period just before it (the same length), so the page can
say whether things went up or down.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.web_deps import require_admin
from app.copy import finance_texts as F
from app.core import clock
from app.core.exceptions import ValidationError
from app.core.jalali import JALALI_MONTHS, format_jalali
from app.db.session import get_db
from app.models import Expense, Payment
from app.services import finance as finance_service
from app.services import payments as payments_service

router = APIRouter(prefix="/api/admin", tags=["finance"], dependencies=[Depends(require_admin)])

MAX_DAYS = 800
DAILY_UP_TO = 45  # a longer period is charted by Jalali month


class Line(BaseModel):
    key: str
    label: str
    amount: int


class Totals(BaseModel):
    income: int
    expenses: int
    net: int


class SeriesPoint(BaseModel):
    key: str
    label: str
    income: int
    expenses: int


class ExpenseLine(BaseModel):
    id: int
    amount: int
    date: str
    category: str
    category_label: str
    note: str | None


class Period(BaseModel):
    kind: str  # month | year | last | range
    label: str
    start: str
    end: str
    days: int
    jy: int  # the Jalali year the period ends in (for the year table)
    jm: int  # ... and its month
    income: int
    income_by_kind: list[Line]
    payments: int
    corrections: int
    expenses: int
    expenses_by_category: list[Line]
    net: int
    previous: Totals
    series: list[SeriesPoint]
    expense_rows: list[ExpenseLine]
    prev_month: tuple[int, int] | None  # only for a month: the neighbours to step to
    next_month: tuple[int, int] | None


def _resolve(
    today: date, jy: int | None, jm: int | None, start: date | None, end: date | None,
    last: int | None,
) -> tuple[str, date, date]:
    if start and end:
        if start > end:
            raise ValidationError("تاریخ شروع باید قبل از پایان باشد")
        return "range", start, min(end, today)
    if last:
        return "last", today - timedelta(days=last - 1), today
    if jy and jm:
        if not 1 <= jm <= 12:
            raise ValidationError("ماه نامعتبر است")
        first, final = finance_service.jalali_month_bounds(jy, jm)
        return "month", first, min(final, today)
    if jy:
        first, _ = finance_service.jalali_month_bounds(jy, 1)
        _, final = finance_service.jalali_month_bounds(jy, 12)
        return "year", first, min(final, today)
    now_y, now_m = finance_service.current_month()
    first, final = finance_service.jalali_month_bounds(now_y, now_m)
    return "month", first, min(final, today)


def _totals(db: Session, first: date, last: date) -> Totals:
    report = finance_service.report_between(db, first, last)
    return Totals(income=report.income, expenses=report.expenses, net=report.net)


def _series(db: Session, first: date, last: date) -> list[SeriesPoint]:
    days = (last - first).days + 1
    by_day = days <= DAILY_UP_TO
    income: dict[str, int] = defaultdict(int)
    spent: dict[str, int] = defaultdict(int)

    def bucket(day: date) -> tuple[str, str]:
        if by_day:
            return day.isoformat(), format_jalali(day)[5:]
        jy, jm = finance_service.month_of(day)
        return f"{jy}-{jm:02d}", JALALI_MONTHS[jm - 1]

    for day, total in db.execute(
        select(Payment.paid_at, func.sum(Payment.amount))
        .where(Payment.paid_at >= first, Payment.paid_at <= last).group_by(Payment.paid_at)
    ):
        income[bucket(day)[0]] += int(total or 0)
    for day, total in db.execute(
        select(Expense.spent_at, func.sum(Expense.amount))
        .where(Expense.spent_at >= first, Expense.spent_at <= last).group_by(Expense.spent_at)
    ):
        spent[bucket(day)[0]] += int(total or 0)

    points: list[SeriesPoint] = []
    seen: set[str] = set()
    day = first
    while day <= last:
        key, label = bucket(day)
        if key not in seen:
            seen.add(key)
            points.append(SeriesPoint(
                key=key, label=label, income=income[key], expenses=spent[key],
            ))
        day += timedelta(days=1)
    return points


@router.get("/finance/period", response_model=Period, operation_id="finance_period")
def finance_period(
    jy: int | None = Query(default=None, ge=1300, le=1500),
    jm: int | None = Query(default=None, ge=1, le=12),
    start: date | None = None,
    end: date | None = None,
    last: int | None = Query(default=None, ge=1, le=MAX_DAYS),
    db: Session = Depends(get_db),
) -> Period:
    today = clock.today()
    kind, first, final = _resolve(today, jy, jm, start, end, last)
    days = (final - first).days + 1
    if days < 1 or days > MAX_DAYS:
        raise ValidationError("بازهٔ انتخاب‌شده معتبر نیست")
    report = finance_service.report_between(db, first, final)

    # The period just before, as long as this one (a month steps to the previous month).
    if kind == "month":
        py, pm = finance_service.shift_month(*finance_service.month_of(first), -1)
        before_first, before_last = finance_service.jalali_month_bounds(py, pm)
    elif kind == "year":
        earlier = finance_service.month_of(first)[0] - 1
        before_first = finance_service.jalali_month_bounds(earlier, 1)[0]
        before_last = finance_service.jalali_month_bounds(earlier, 12)[1]
    else:
        before_last = first - timedelta(days=1)
        before_first = before_last - timedelta(days=days - 1)

    if kind == "month":
        jy_, jm_ = finance_service.month_of(first)
        label = f"{JALALI_MONTHS[jm_ - 1]} {jy_}"
        now = finance_service.current_month()
        following = finance_service.shift_month(jy_, jm_, 1)
        prev_month = finance_service.shift_month(jy_, jm_, -1)
        next_month = following if following <= now else None
    elif kind == "year":
        label = f"سال {finance_service.month_of(first)[0]}"
        prev_month = next_month = None
    elif kind == "last":
        label = f"{days} روز اخیر"
        prev_month = next_month = None
    else:
        label = f"{format_jalali(first)} تا {format_jalali(final)}"
        prev_month = next_month = None

    expenses = db.scalars(
        select(Expense).where(Expense.spent_at >= first, Expense.spent_at <= final)
        .order_by(Expense.spent_at.desc(), Expense.id.desc())
    )
    return Period(
        kind=kind, label=label, start=first.isoformat(), end=final.isoformat(), days=days,
        jy=finance_service.month_of(final)[0], jm=finance_service.month_of(final)[1],
        income=report.income,
        income_by_kind=[
            Line(key=k.value, label=payments_service.kind_label(k), amount=v)
            for k, v in report.income_by_kind.items() if v
        ],
        payments=report.payment_count, corrections=report.correction_count,
        expenses=report.expenses,
        expenses_by_category=[
            Line(key=k.value, label=F.CATEGORY_LABELS[k.value], amount=v)
            for k, v in report.expenses_by_category.items() if v
        ],
        net=report.net, previous=_totals(db, before_first, before_last),
        series=_series(db, first, final),
        expense_rows=[
            ExpenseLine(
                id=e.id, amount=e.amount, date=format_jalali(e.spent_at),
                category=e.category.value, category_label=F.CATEGORY_LABELS[e.category.value],
                note=e.note,
            )
            for e in expenses
        ],
        prev_month=prev_month, next_month=next_month,
    )
