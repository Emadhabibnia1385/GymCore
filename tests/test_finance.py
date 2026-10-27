"""Finance: the gym's expenses (append-only) and the monthly money report.

Month bounds are checked against core/jalali.py's own leap years. The report
math covers every payment kind, negative corrections on both sides of the
ledger, and a month's first and last days. The bot screens are driven end to
end through the dispatcher — tampered and stale callbacks included — on both
platforms. Dates the coach types are relative to today, so the suite passes on
whatever day it runs.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import func, select

from app.copy import admin_texts as A
from app.copy import finance_texts as F
from app.copy import texts
from app.core.exceptions import ValidationError
from app.core.jalali import (
    JALALI_MONTHS,
    format_jalali,
    gregorian_to_jalali,
    jalali_to_gregorian,
    parse_jalali,
)
from app.models import Expense, ExpenseCategory, PaymentKind, Platform
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import finance as finance_service
from app.services import payments as payments_service
from app.services import persons as persons_service
from tests.fakes import (
    button_texts,
    callback_update,
    last_markup,
    last_text,
    make_dispatcher,
    message_update,
    photo_message_update,
    register,
)

OWNER = 111
BALE_OWNER = 333  # BALE_OWNER_IDS in conftest
CHAT = 900
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


def _token(month):
    return f"{month[0]:04d}{month[1]:02d}"


def _title(month):
    return F.REPORT_TITLE.format(month=JALALI_MONTHS[month[1] - 1], year=month[0])


def _callbacks(client):
    return [b["callback_data"] for row in last_markup(client)["inline_keyboard"] for b in row]


def _data_of(client, label):
    """The callback behind the button labelled `label` on the last screen."""
    for row in last_markup(client)["inline_keyboard"]:
        for button in row:
            if button["text"] == label:
                return button["callback_data"]
    raise AssertionError(f"no «{label}» among {button_texts(last_markup(client))}")


def _items(client):
    """The expense lines of the last screen."""
    return [line for line in last_text(client).splitlines() if line.startswith("• ")]


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


def test_month_report_screen(db):
    _seed_mehr_1405(db)
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:fin:m:140507"))
    lines = last_text(client).splitlines()
    assert lines[0] == "📊 گزارش مالی — مهر 1405"
    for line in (
        "💰 درآمد: 1,150,000 تومان",
        "• شهریه: 900,000 تومان",
        "• ورودی باشگاه: 200,000 تومان",
        "• سایر: 50,000 تومان",
        "🔢 تعداد پرداخت‌ها: 3 (و 1 اصلاحیه)",
        "💸 هزینه: 2,250,000 تومان",
        "• اجاره: 2,000,000 تومان",
        "• تجهیزات: 250,000 تومان",
        "🔴 سود خالص: -1,100,000 تومان",
    ):
        assert line in lines
    assert "تبلیغات" not in last_text(client)  # nothing spent there in Mehr: not listed
    disp.handle_update(callback_update(2, CHAT, OWNER, "a:fin:m:140508"))
    assert "🟢 سود خالص: 111,000 تومان" in last_text(client)  # a profit is green


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


# --- the payments front page ---


def test_payments_front_page_still_lists_debts_then_finance(db):
    _student(db, "سارا", tuition=500_000)
    _student(db, "مریم", tuition=2_000_000)
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:pay"))
    labels = button_texts(last_markup(client))
    assert labels[0].startswith("مریم") and labels[1].startswith("سارا")  # largest first
    assert "2 دوره هنوز بدهی دارد" in last_text(client)
    assert labels[2:] == [F.BTN_MONTH_REPORT, F.BTN_NEW_EXPENSE, A.BACK]


def test_finance_is_reachable_when_nobody_owes(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:pay"))
    assert A.PAYMENTS_ALL_SETTLED in last_text(client)
    disp.handle_update(callback_update(2, CHAT, OWNER, _data_of(client, F.BTN_MONTH_REPORT)))
    assert last_text(client).startswith(_title(finance_service.current_month()))


# --- the expense flow, end to end ---


def test_recording_an_expense_end_to_end(db):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:pay"))
    disp.handle_update(callback_update(2, CHAT, OWNER, _data_of(client, F.BTN_NEW_EXPENSE)))
    assert last_text(client) == F.ASK_AMOUNT
    disp.handle_update(message_update(3, CHAT, OWNER, "۲٬۵۰۰٬۰۰۰"))  # Persian digits are fine
    assert last_text(client) == F.ASK_CATEGORY.format(amount="2,500,000 تومان")
    assert set(F.CATEGORY_LABELS.values()) <= set(button_texts(last_markup(client)))
    disp.handle_update(callback_update(4, CHAT, OWNER, _data_of(client, F.CATEGORY_LABELS["RENT"])))
    today = F.BTN_TODAY.format(date=format_jalali(date.today()))
    disp.handle_update(callback_update(5, CHAT, OWNER, _data_of(client, today)))
    assert last_text(client) == F.ASK_NOTE
    disp.handle_update(message_update(6, CHAT, OWNER, "اجارهٔ سالن"))

    db.expire_all()
    (expense,) = db.scalars(select(Expense)).all()
    assert (expense.amount, expense.category, expense.spent_at, expense.note) == (
        2_500_000, ExpenseCategory.RENT, date.today(), "اجارهٔ سالن"
    )
    assert expense.created_by == str(OWNER)
    # Saved: the month's report, with the result as a flash line on top.
    lines = last_text(client).splitlines()
    assert lines[0] == F.EXPENSE_SAVED.format(category="اجاره", amount="2,500,000 تومان")
    assert lines[2] == _title(finance_service.current_month())
    assert "• اجاره: 2,500,000 تومان" in lines


def test_a_negative_amount_records_a_correction(db):
    yesterday = date.today() - timedelta(days=1)
    month = finance_service.month_of(yesterday)
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:fin:new:{_token(month)}"))
    disp.handle_update(message_update(2, CHAT, OWNER, "-۳۰۰۰۰۰"))
    disp.handle_update(callback_update(3, CHAT, OWNER, "a:fin:cat:EQUIPMENT"))
    disp.handle_update(message_update(4, CHAT, OWNER, format_jalali(yesterday)))  # typed
    disp.handle_update(callback_update(5, CHAT, OWNER, "a:fin:skip"))

    db.expire_all()
    (expense,) = db.scalars(select(Expense)).all()
    assert (expense.amount, expense.spent_at, expense.note) == (-300_000, yesterday, None)
    text = last_text(client)
    assert text.startswith(F.CORRECTION_SAVED.format(category="تجهیزات", amount="-300,000 تومان"))
    assert _title(month) in text and "💸 هزینه: -300,000 تومان" in text
    # A second tap on «⏭ رد کردن» finds the step gone — never a second row.
    disp.handle_update(callback_update(6, CHAT, OWNER, "a:fin:skip"))
    assert last_text(client) == F.STEP_EXPIRED
    assert _expense_count(db) == 1


def test_the_flow_refuses_bad_input_and_keeps_its_place(db):
    today = date.today()
    jy, jm, jd = gregorian_to_jalali(today.year, today.month, today.day)
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:fin:new"))
    disp.handle_update(message_update(2, CHAT, OWNER, "0"))
    assert last_text(client) == f"{F.AMOUNT_ZERO}\n{F.ASK_AMOUNT}"
    disp.handle_update(message_update(3, CHAT, OWNER, "صد هزار"))
    assert last_text(client) == f"{A.INVALID_NUMBER}\n{F.ASK_AMOUNT}"
    disp.handle_update(message_update(4, CHAT, OWNER, "1" + "0" * 13))
    assert last_text(client).startswith(F.AMOUNT_TOO_LARGE)
    disp.handle_update(message_update(5, CHAT, OWNER, "100000"))
    disp.handle_update(callback_update(6, CHAT, OWNER, "a:fin:cat:HACKED"))  # tampered
    assert last_text(client) == F.ASK_CATEGORY.format(amount="100,000 تومان")  # asked again
    disp.handle_update(callback_update(7, CHAT, OWNER, "a:fin:cat:BILLS"))
    disp.handle_update(message_update(8, CHAT, OWNER, format_jalali(today + timedelta(days=1))))
    assert last_text(client) == f"{F.DATE_IN_FUTURE}\n{F.ASK_DATE}"
    # Today's day and month with last year's number: the typo a screen showing
    # «۵ آبان» never reveals.
    disp.handle_update(message_update(9, CHAT, OWNER, f"{jy - 1}/{jm:02d}/{min(jd, 29):02d}"))
    assert last_text(client) == f"{F.DATE_TOO_OLD}\n{F.ASK_DATE}"
    disp.handle_update(message_update(10, CHAT, OWNER, "1405/13/40"))
    assert last_text(client) == f"{A.INVALID_DATE}\n{F.ASK_DATE}"
    assert _expense_count(db) == 0
    # Still at the date step: «📅 امروز» moves on; a photo is not a note.
    disp.handle_update(callback_update(11, CHAT, OWNER, "a:fin:today"))
    disp.handle_update(photo_message_update(12, CHAT, OWNER))
    assert last_text(client) == f"{F.NOTE_NEEDS_TEXT}\n{F.ASK_NOTE}"
    disp.handle_update(message_update(13, CHAT, OWNER, "قبض آب"))
    assert _expense_count(db) == 1


def test_every_prompt_has_a_way_out(db):
    month = finance_service.current_month()
    disp, client = make_dispatcher()
    # Started from a month's report, «✖️ لغو» goes back to that month...
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:fin:new:{_token(month)}"))
    assert _callbacks(client) == [f"a:fin:m:{_token(month)}"]
    disp.handle_update(message_update(2, CHAT, OWNER, "500000"))
    assert _data_of(client, A.CANCEL) == f"a:fin:m:{_token(month)}"
    disp.handle_update(callback_update(3, CHAT, OWNER, "a:fin:cat:OTHER"))
    assert _data_of(client, A.CANCEL) == f"a:fin:m:{_token(month)}"
    disp.handle_update(callback_update(4, CHAT, OWNER, "a:fin:today"))
    assert _data_of(client, A.CANCEL) == f"a:fin:m:{_token(month)}"
    disp.handle_update(callback_update(5, CHAT, OWNER, _data_of(client, A.CANCEL)))
    assert last_text(client).startswith(_title(month))
    # ...and the next message is no longer taken as the note.
    disp.handle_update(message_update(6, CHAT, OWNER, "یادداشتی که نباید ثبت شود"))
    assert _expense_count(db) == 0
    # Started from the payments page, it goes back there.
    disp.handle_update(callback_update(7, CHAT, OWNER, "a:fin:new"))
    assert _callbacks(client) == ["a:pay"]


def test_stale_taps_explain_themselves(db):
    disp, client = make_dispatcher()
    for update_id, data in enumerate(("a:fin:today", "a:fin:skip", "a:fin:cat:RENT"), start=1):
        disp.handle_update(callback_update(update_id, CHAT, OWNER, data))
        assert last_text(client) == F.STEP_EXPIRED
        assert F.BTN_NEW_EXPENSE in button_texts(last_markup(client))
    assert _expense_count(db) == 0


# --- navigation ---


def test_month_navigation_never_runs_past_this_month(db):
    month = finance_service.current_month()
    previous = finance_service.shift_month(*month, -1)
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, "a:fin:m"))
    assert last_text(client).startswith(_title(month))
    labels = button_texts(last_markup(client))
    assert F.BTN_PREV_MONTH in labels and F.BTN_NEXT_MONTH not in labels
    disp.handle_update(callback_update(2, CHAT, OWNER, _data_of(client, F.BTN_PREV_MONTH)))
    assert last_text(client).startswith(_title(previous))
    assert _data_of(client, F.BTN_NEXT_MONTH) == f"a:fin:m:{_token(month)}"
    # A month that hasn't happened yet is shown as this one.
    following = finance_service.shift_month(*month, 1)
    disp.handle_update(callback_update(3, CHAT, OWNER, f"a:fin:m:{_token(following)}"))
    assert last_text(client).startswith(_title(month))


def test_year_summary_screen(db):
    month = finance_service.current_month()
    jy, jm = month
    sara, _ = _student(db)
    _pay(db, sara, 1_200_000, PaymentKind.TUITION, date.today())
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:fin:m:{_token(month)}"))
    disp.handle_update(callback_update(2, CHAT, OWNER, _data_of(client, F.BTN_YEAR_SUMMARY)))
    lines = last_text(client).splitlines()
    assert lines[0] == F.YEAR_TITLE.format(year=jy)
    assert all(any(line.startswith(f"{name}:") for line in lines) for name in JALALI_MONTHS)
    assert f"{JALALI_MONTHS[jm - 1]}: 1,200,000 / 0 / 🟢 1,200,000" in lines
    assert F.YEAR_TOTAL.format(income="1,200,000", expenses="0", net="🟢 1,200,000") in lines
    # Months up to this one open their report; the ones still ahead don't.
    months = [label for label in button_texts(last_markup(client)) if label in JALALI_MONTHS]
    assert months == list(JALALI_MONTHS[:jm])
    assert _data_of(client, A.BACK) == f"a:fin:m:{_token(month)}"
    # Last year is whole: all twelve open.
    disp.handle_update(callback_update(3, CHAT, OWNER, f"a:fin:y:{jy - 1}12"))
    assert last_text(client).startswith(F.YEAR_TITLE.format(year=jy - 1))
    months = [label for label in button_texts(last_markup(client)) if label in JALALI_MONTHS]
    assert months == list(JALALI_MONTHS)


def test_expense_list_is_newest_first_and_paged(db):
    month = finance_service.shift_month(*finance_service.current_month(), -1)
    first, _ = finance_service.jalali_month_bounds(*month)
    finance_service.record_expense(db, 100_000, ExpenseCategory.BILLS, first, note="قبض برق")
    finance_service.record_expense(db, 300_000, ExpenseCategory.OTHER, first + timedelta(days=2))
    finance_service.record_expense(
        db, 200_000, ExpenseCategory.ADS, first + timedelta(days=1), note="آگهی " * 30
    )
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:fin:m:{_token(month)}"))
    disp.handle_update(callback_update(2, CHAT, OWNER, _data_of(client, F.BTN_MONTH_EXPENSES)))
    text = last_text(client)
    assert text.startswith(
        F.EXPENSES_TITLE.format(month=JALALI_MONTHS[month[1] - 1], year=month[0])
    )
    assert F.EXPENSES_TOTAL.format(amount="600,000 تومان", n=3) in text
    items = _items(client)
    assert [label for item in items for label in ("سایر", "تبلیغات", "قبوض") if label in item] == [
        "سایر", "تبلیغات", "قبوض",
    ]
    assert items[1].endswith("…")  # a long note is cut short in the list

    for _ in range(15):
        finance_service.record_expense(db, 1_000, ExpenseCategory.OTHER, first + timedelta(days=3))
    disp.handle_update(callback_update(3, CHAT, OWNER, f"a:fin:x:{_token(month)}"))
    assert len(_items(client)) == 15
    disp.handle_update(callback_update(4, CHAT, OWNER, _data_of(client, A.NEXT)))
    assert len(_items(client)) == 3 and "قبوض" in _items(client)[-1]  # the oldest, last
    disp.handle_update(callback_update(5, CHAT, OWNER, f"a:fin:x:{_token(month)}:page:99"))
    assert len(_items(client)) == 3  # past the end: the last page


def test_an_empty_month_says_so(db):
    month = finance_service.current_month()
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, f"a:fin:x:{_token(month)}"))
    assert F.EXPENSES_EMPTY in last_text(client)
    assert _data_of(client, F.BTN_NEW_EXPENSE) == f"a:fin:new:{_token(month)}"


# --- tamper safety, limits, access, platforms ---


@pytest.mark.parametrize("data", [
    "a:fin",
    "a:fin:m:140513",
    "a:fin:m:140500",
    "a:fin:m:abc",
    "a:fin:m:۱۴۰۵۰۸",
    "a:fin:m:²²²²²²",
    "a:fin:m:999999",
    "a:fin:m:000001",
    "a:fin:m:14050801",
    "a:fin:zzz:1:2:3",
])
def test_a_garbled_month_shows_this_month(db, data):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, data))
    assert last_text(client).startswith(_title(finance_service.current_month()))


@pytest.mark.parametrize("data", [
    "a:fin:y:zz",
    "a:fin:y:",
    "a:fin:x:1405",
    "a:fin:x:140508:page:abc",
    "a:fin:x:140508:page:-3",
    "a:fin:x:140508:page:99999999999999999999",
    "a:fin:x:140508:pg:2",
    "a:fin:new:¹²³",
    "a:fin:cat:",
    "a:fin:today:extra",
])
def test_tampered_callbacks_never_crash(db, data):
    disp, client = make_dispatcher()
    disp.handle_update(callback_update(1, CHAT, OWNER, data))
    assert client.sent and last_text(client) != texts.ERROR
    assert _expense_count(db) == 0


def test_every_finance_callback_fits_in_64_bytes(db):
    month = finance_service.current_month()
    disp, client = make_dispatcher()
    for update_id, data in enumerate((
        "a:pay", "a:fin:m", f"a:fin:y:{_token(month)}", f"a:fin:y:{month[0] - 1}12",
        f"a:fin:x:{_token(month)}", f"a:fin:new:{_token(month)}",
    ), start=1):
        disp.handle_update(callback_update(update_id, CHAT, OWNER, data))
    disp.handle_update(message_update(10, CHAT, OWNER, "1000"))
    disp.handle_update(callback_update(11, CHAT, OWNER, "a:fin:cat:EQUIPMENT"))
    disp.handle_update(callback_update(12, CHAT, OWNER, "a:fin:today"))
    sent = [
        button["callback_data"]
        for message in client.sent if message.get("reply_markup")
        for row in message["reply_markup"]["inline_keyboard"]
        for button in row
    ]
    assert sent and all(len(data.encode()) <= 64 for data in sent)


def test_non_owners_never_reach_finance(db):
    disp, client = make_dispatcher()
    register(disp, 500, 700)
    before = len(client.sent)
    disp.handle_update(callback_update(1, 500, 700, "a:fin:m"))
    assert client.answered[-1]["text"] == texts.ACCESS_DENIED
    assert len(client.sent) == before


def test_bale_owner_records_an_expense_too(db):
    disp, client = make_dispatcher(Platform.BALE)
    disp.handle_update(callback_update(1, CHAT, BALE_OWNER, "a:pay"))
    disp.handle_update(callback_update(2, CHAT, BALE_OWNER, _data_of(client, F.BTN_NEW_EXPENSE)))
    disp.handle_update(message_update(3, CHAT, BALE_OWNER, "150000"))
    disp.handle_update(callback_update(4, CHAT, BALE_OWNER, "a:fin:cat:SALARY"))
    disp.handle_update(callback_update(5, CHAT, BALE_OWNER, "a:fin:today"))
    disp.handle_update(callback_update(6, CHAT, BALE_OWNER, "a:fin:skip"))
    db.expire_all()
    (expense,) = db.scalars(select(Expense)).all()
    assert (expense.category, expense.created_by) == (ExpenseCategory.SALARY, str(BALE_OWNER))
    saved = F.EXPENSE_SAVED.format(category="حقوق", amount="150,000 تومان")
    assert last_text(client).startswith(saved)
    assert all(message["method"] == "send_message" for message in client.sent)  # never edits
    assert not any("style" in b for row in last_markup(client)["inline_keyboard"] for b in row)
