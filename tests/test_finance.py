"""Finance: the gym's expenses (append-only) and the monthly money report.

Month bounds are checked against core/jalali.py's own leap years. The report
math covers every payment kind, negative corrections on both sides of the
ledger, and a month's first and last days. Dates the coach types are relative
to today, so the suite passes on whatever day it runs.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.core.exceptions import ValidationError
from app.core.jalali import gregorian_to_jalali, jalali_to_gregorian, parse_jalali
from app.models import Expense, ExpenseCategory, PaymentKind
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import finance as finance_service
from app.services import payments as payments_service
from app.services import persons as persons_service

MEHR_1405 = (date(2026, 9, 23), date(2026, 10, 22))


def _student(db, name="سارا", tuition=1_000_000):
    client = persons_service.create(db, name=name)
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=client.id, class_type_id=class_type.id, sessions_total=12,
        tuition=tuition, start_date=date(2026, 7, 25),
    )
    return client, course


def _pay(db, client, amount, kind, day):
    payments_service.record(db, client.id, amount, kind, day, notify=False)


def _expense_row(db, amount, category, day):
    """An expense on a fixed day, straight into the table: record_expense only
    takes dates within a year of *today*."""
    db.add(Expense(amount=amount, category=category, spent_at=day))
    db.commit()


def _expense_count(db):
    db.expire_all()
    return db.scalar(select(func.count()).select_from(Expense))


# --- Jalali month bounds ---


def test_month_bounds_of_farvardin_and_mehr():
    assert finance_service.jalali_month_bounds(1405, 1) == (date(2026, 3, 21), date(2026, 4, 20))
    assert finance_service.jalali_month_bounds(1405, 7) == MEHR_1405
    assert finance_service.jalali_month_bounds(1404, 1) == (date(2025, 3, 21), date(2025, 4, 20))


def test_esfand_has_30_days_in_a_leap_year_and_29_otherwise():
    assert finance_service.jalali_month_bounds(1403, 12) == (date(2025, 2, 19), date(2025, 3, 20))
    assert finance_service.jalali_month_bounds(1404, 12) == (date(2026, 2, 20), date(2026, 3, 20))
    leap_years = []
    for jy in range(1395, 1412):
        first, last = finance_service.jalali_month_bounds(jy, 12)
        leap = parse_jalali(f"{jy}/12/30") is not None  # core/jalali.py decides
        leap_years += [jy] if leap else []
        assert (last - first).days + 1 == (30 if leap else 29)
        assert gregorian_to_jalali(last.year, last.month, last.day) == (jy, 12, 30 if leap else 29)
        assert last + timedelta(days=1) == jalali_to_gregorian(jy + 1, 1, 1)
    assert leap_years == [1395, 1399, 1403, 1408]  # the real calendar's


def test_months_tile_the_year_without_a_gap():
    for jy in (1403, 1404, 1405):
        previous_last = finance_service.jalali_month_bounds(jy - 1, 12)[1]
        days = 0
        for jm in range(1, 13):
            first, last = finance_service.jalali_month_bounds(jy, jm)
            assert first == previous_last + timedelta(days=1)
            assert gregorian_to_jalali(first.year, first.month, first.day) == (jy, jm, 1)
            days += (last - first).days + 1
            previous_last = last
        assert days == (366 if parse_jalali(f"{jy}/12/30") else 365)


def test_a_month_that_does_not_exist_has_no_bounds():
    for jm in (0, 13):
        with pytest.raises(ValueError):
            finance_service.jalali_month_bounds(1405, jm)


def test_shifting_months_crosses_year_ends():
    assert finance_service.shift_month(1405, 1, -1) == (1404, 12)
    assert finance_service.shift_month(1404, 12, 1) == (1405, 1)
    assert finance_service.shift_month(1405, 8, -20) == (1403, 12)


# --- report math ---


def _seed_mehr_1405(db):
    """Mehr 1405 with every payment kind, a correction on each side, and rows
    on the days just outside it."""
    first, last = MEHR_1405
    sara, _ = _student(db)
    _pay(db, sara, 1_000_000, PaymentKind.TUITION, first)  # the first day counts
    _pay(db, sara, 200_000, PaymentKind.GYM_FEE, date(2026, 10, 1))
    _pay(db, sara, 50_000, PaymentKind.OTHER, last)  # and so does the last
    _pay(db, sara, -100_000, PaymentKind.TUITION, date(2026, 10, 5))  # a correction
    _pay(db, sara, 999_000, PaymentKind.TUITION, first - timedelta(days=1))  # Shahrivar
    _pay(db, sara, 888_000, PaymentKind.TUITION, last + timedelta(days=1))  # Aban
    _expense_row(db, 2_000_000, ExpenseCategory.RENT, first)
    _expense_row(db, 300_000, ExpenseCategory.EQUIPMENT, date(2026, 10, 10))
    _expense_row(db, -50_000, ExpenseCategory.EQUIPMENT, date(2026, 10, 11))  # a correction
    _expense_row(db, 777_000, ExpenseCategory.ADS, last + timedelta(days=1))  # Aban


def test_month_report_sums_kinds_categories_and_corrections(db):
    _seed_mehr_1405(db)
    report = finance_service.month_report(db, 1405, 7)
    assert (report.first_day, report.last_day) == MEHR_1405
    assert report.income == 1_150_000
    assert report.income_by_kind == {
        PaymentKind.TUITION: 900_000, PaymentKind.GYM_FEE: 200_000, PaymentKind.OTHER: 50_000,
    }
    assert (report.payment_count, report.correction_count) == (3, 1)
    assert report.expenses == 2_250_000
    assert report.expenses_by_category == {
        ExpenseCategory.RENT: 2_000_000, ExpenseCategory.EQUIPMENT: 250_000,
        ExpenseCategory.SALARY: 0, ExpenseCategory.ADS: 0, ExpenseCategory.BILLS: 0,
        ExpenseCategory.OTHER: 0,
    }
    assert report.expense_count == 3
    assert report.net == -1_100_000
    # The rows just outside Mehr landed in their own months.
    assert finance_service.month_report(db, 1405, 6).income == 999_000
    aban = finance_service.month_report(db, 1405, 8)
    assert (aban.income, aban.expenses, aban.net) == (888_000, 777_000, 111_000)


def test_year_overview_has_twelve_rows_that_match_the_month_reports(db):
    sara, _ = _student(db)
    _pay(db, sara, 500_000, PaymentKind.TUITION, date(2026, 3, 21))  # 1405/01/01
    _pay(db, sara, 300_000, PaymentKind.TUITION, date(2026, 3, 20))  # 1404/12/29: last year
    _pay(db, sara, 400_000, PaymentKind.GYM_FEE, date(2026, 10, 1))  # Mehr
    _pay(db, sara, -100_000, PaymentKind.GYM_FEE, date(2026, 10, 2))  # Mehr, a correction
    _pay(db, sara, 700_000, PaymentKind.OTHER, date(2027, 3, 20))  # 1405/12/29: Esfand's last
    _pay(db, sara, 600_000, PaymentKind.OTHER, date(2027, 3, 21))  # 1406/01/01: next year
    _expense_row(db, 1_000_000, ExpenseCategory.RENT, date(2026, 10, 3))  # Mehr
    _expense_row(db, 250_000, ExpenseCategory.BILLS, date(2026, 4, 20))  # 1405/01/31

    rows = finance_service.year_overview(db, 1405)
    assert [row.jm for row in rows] == list(range(1, 13))
    by_month = {row.jm: (row.income, row.expenses, row.net) for row in rows}
    assert by_month[1] == (500_000, 250_000, 250_000)
    assert by_month[7] == (300_000, 1_000_000, -700_000)
    assert by_month[12] == (700_000, 0, 700_000)
    assert all(by_month[jm] == (0, 0, 0) for jm in (2, 3, 4, 5, 6, 8, 9, 10, 11))
    for row in rows:
        report = finance_service.month_report(db, 1405, row.jm)
        assert (row.income, row.expenses) == (report.income, report.expenses)


# --- recording expenses: validation, append-only ---


def test_record_expense_refuses_zero_the_future_and_a_year_back(db):
    today = date.today()
    for amount, day in (
        (0, today),
        (100_000, today + timedelta(days=1)),
        (100_000, today - timedelta(days=365)),  # a mistyped year lands here
        (10**13, today),
    ):
        with pytest.raises(ValidationError):
            finance_service.record_expense(db, amount, ExpenseCategory.RENT, day)
    with pytest.raises(TypeError):  # money is integer Toman, never a float
        finance_service.record_expense(db, 1.5, ExpenseCategory.RENT, today)
    assert _expense_count(db) == 0

    kept = finance_service.record_expense(
        db, -40_000, ExpenseCategory.BILLS, today - timedelta(days=364),
        note="  اصلاح قبض  ", created_by="111",
    )
    assert (kept.amount, kept.note, kept.created_by) == (-40_000, "اصلاح قبض", "111")


def test_expenses_are_append_only():
    mutators = ("update", "delete", "edit", "remove")
    assert not [name for name in dir(finance_service) if name.startswith(mutators)]
