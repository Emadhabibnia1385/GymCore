"""Gym finance: the coach's expenses and the monthly income report.

Expenses follow the payment rules — APPEND-ONLY. There is deliberately no update
or delete: a wrong entry is corrected by recording a negative expense in the
same category.

Nothing here is stored as a total. A report sums the immutable payment history
(negative corrections included) and the expense history over the Gregorian days
of one Jalali month, so it always agrees with the payments screens.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import Select, case, func, select
from sqlalchemy.orm import Session

from app.copy import finance_texts as F
from app.core import clock
from app.core.exceptions import ValidationError
from app.core.jalali import gregorian_to_jalali, jalali_to_gregorian
from app.models import Expense, ExpenseCategory, Payment, PaymentKind

# An expense is dated today or within the year before it. The year is the typo
# nobody sees — «1404/08/05» for «1405/08/05» — and it would silently move the
# cost into last year's report, so a date a full year back is refused.
MAX_AGE_DAYS = 365
# Far beyond any real expense: a guard against a run of mistyped zeros (and a
# number too large for the 64-bit column).
MAX_AMOUNT = 10**12


@dataclass(frozen=True)
class MonthReport:
    """One Jalali month's money: what came in, what went out, what is left."""

    jy: int
    jm: int
    first_day: date
    last_day: date
    income: int
    income_by_kind: dict[PaymentKind, int]
    # Payments received (positive rows); the negative corrections among the
    # month's rows are counted apart, though both are in `income`.
    payment_count: int
    correction_count: int
    expenses: int
    expenses_by_category: dict[ExpenseCategory, int]
    expense_count: int

    @property
    def net(self) -> int:
        return self.income - self.expenses


@dataclass(frozen=True)
class MonthTotals:
    """One row of the year overview."""

    jm: int
    income: int
    expenses: int

    @property
    def net(self) -> int:
        return self.income - self.expenses


# --- Jalali months ---


def jalali_month_bounds(jy: int, jm: int) -> tuple[date, date]:
    """The first and last Gregorian day of Jalali month `jm` of year `jy`.

    The last day is the day before the next month begins, so Esfand comes out 29
    or 30 days long exactly as core/jalali.py counts leap years.
    """
    if not 1 <= jm <= 12:
        raise ValueError(f"Jalali month out of range: {jm}")
    first = jalali_to_gregorian(jy, jm, 1)
    if jm == 12:
        following = jalali_to_gregorian(jy + 1, 1, 1)
    else:
        following = jalali_to_gregorian(jy, jm + 1, 1)
    return first, following - timedelta(days=1)


def month_of(day: date) -> tuple[int, int]:
    """The Jalali (year, month) a Gregorian day falls in."""
    jy, jm, _ = gregorian_to_jalali(day.year, day.month, day.day)
    return jy, jm


def current_month() -> tuple[int, int]:
    return month_of(clock.today())


def shift_month(jy: int, jm: int, months: int) -> tuple[int, int]:
    """(jy, jm) moved by `months` (negative = back), across year ends."""
    index = jy * 12 + (jm - 1) + months
    return index // 12, index % 12 + 1


# --- expenses (append-only) ---


def check_amount(amount: int) -> int:
    """An expense amount: integer Toman, never zero (negative = a correction)."""
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise TypeError("an expense amount is integer Toman")
    if amount == 0:
        raise ValidationError(F.AMOUNT_ZERO)
    if abs(amount) > MAX_AMOUNT:
        raise ValidationError(F.AMOUNT_TOO_LARGE)
    return amount


def check_spent_at(spent_at: date) -> date:
    """An expense date: not in the future, and less than a year ago."""
    if isinstance(spent_at, datetime):
        spent_at = spent_at.date()
    today = clock.today()
    if spent_at > today:
        raise ValidationError(F.DATE_IN_FUTURE)
    if spent_at <= today - timedelta(days=MAX_AGE_DAYS):
        raise ValidationError(F.DATE_TOO_OLD)
    return spent_at


def record_expense(
    db: Session,
    amount: int,
    category: ExpenseCategory,
    spent_at: date,
    note: str | None = None,
    created_by: str | None = None,
) -> Expense:
    """Append one expense. A wrong entry is fixed with a negative one, never edited."""
    amount = check_amount(amount)
    spent_at = check_spent_at(spent_at)
    expense = Expense(
        amount=amount,
        category=ExpenseCategory(category),
        spent_at=spent_at,
        note=(note or "").strip() or None,
        created_by=created_by,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense


def expenses_stmt(jy: int, jm: int) -> Select:
    """One month's expenses, newest first (for pagination)."""
    first, last = jalali_month_bounds(jy, jm)
    return (
        select(Expense)
        .where(Expense.spent_at >= first, Expense.spent_at <= last)
        .order_by(Expense.spent_at.desc(), Expense.id.desc())
    )


def list_expenses(db: Session, jy: int, jm: int) -> list[Expense]:
    return list(db.scalars(expenses_stmt(jy, jm)))


# --- reports ---


def month_report(db: Session, jy: int, jm: int) -> MonthReport:
    """Income (by payment kind) and expenses (by category) of one Jalali month."""
    first, last = jalali_month_bounds(jy, jm)

    income_by_kind = dict.fromkeys(PaymentKind, 0)
    payment_count = correction_count = 0
    payment_rows = db.execute(
        select(
            Payment.kind,
            func.sum(Payment.amount),
            func.sum(case((Payment.amount > 0, 1), else_=0)),
            func.sum(case((Payment.amount < 0, 1), else_=0)),
        )
        .where(Payment.paid_at >= first, Payment.paid_at <= last)
        .group_by(Payment.kind)
    )
    for kind, total, received, corrections in payment_rows:
        income_by_kind[kind] += int(total or 0)
        payment_count += int(received or 0)
        correction_count += int(corrections or 0)

    expenses_by_category = dict.fromkeys(ExpenseCategory, 0)
    expense_count = 0
    expense_rows = db.execute(
        select(Expense.category, func.sum(Expense.amount), func.count(Expense.id))
        .where(Expense.spent_at >= first, Expense.spent_at <= last)
        .group_by(Expense.category)
    )
    for category, total, count in expense_rows:
        expenses_by_category[category] += int(total or 0)
        expense_count += int(count or 0)

    return MonthReport(
        jy=jy,
        jm=jm,
        first_day=first,
        last_day=last,
        income=sum(income_by_kind.values()),
        income_by_kind=income_by_kind,
        payment_count=payment_count,
        correction_count=correction_count,
        expenses=sum(expenses_by_category.values()),
        expenses_by_category=expenses_by_category,
        expense_count=expense_count,
    )


def year_overview(db: Session, jy: int) -> list[MonthTotals]:
    """Twelve rows — Farvardin to Esfand — of income, expenses and net."""
    first, _ = jalali_month_bounds(jy, 1)
    _, last = jalali_month_bounds(jy, 12)
    income = [0] * 12
    expenses = [0] * 12
    # One query per table: totals per day, bucketed into Jalali months here.
    for day, total in db.execute(
        select(Payment.paid_at, func.sum(Payment.amount))
        .where(Payment.paid_at >= first, Payment.paid_at <= last)
        .group_by(Payment.paid_at)
    ):
        income[month_of(day)[1] - 1] += int(total or 0)
    for day, total in db.execute(
        select(Expense.spent_at, func.sum(Expense.amount))
        .where(Expense.spent_at >= first, Expense.spent_at <= last)
        .group_by(Expense.spent_at)
    ):
        expenses[month_of(day)[1] - 1] += int(total or 0)
    return [
        MonthTotals(jm=jm, income=income[jm - 1], expenses=expenses[jm - 1])
        for jm in range(1, 13)
    ]
