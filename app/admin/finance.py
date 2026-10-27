"""Admin section «fin»: the monthly money report and recording the gym's expenses.

Reached from the payments front page («📊 گزارش ماه» / «➖ ثبت هزینه»). Every
figure is derived on the fly by services/finance.py; expenses are append-only,
so a wrong one is corrected with a negative entry, never edited.

Callbacks (a Jalali month travels as a `YYYYMM` token, e.g. 140508):
  a:fin:m[:YYYYMM]          month report — this month by default, never a later one
  a:fin:y:YYYYMM            that month's year, as a 12-month table (back → the month)
  a:fin:x:YYYYMM[:page:N]   that month's expenses, newest first
  a:fin:new[:YYYYMM]        record an expense («✖️ لغو» → that month, else payments)
  a:fin:cat:<CATEGORY>      the category step
  a:fin:today               «📅 امروز» on the date step
  a:fin:skip                «⏭ رد کردن» on the note step — saves
"""

from __future__ import annotations

from datetime import date

from app.admin import common
from app.admin.common import AdminReq
from app.bots.common import callbacks as cb
from app.bots.common import formatting
from app.copy import admin_texts as A
from app.copy import finance_texts as F
from app.core import clock
from app.core.exceptions import ValidationError
from app.core.jalali import JALALI_MONTHS, format_jalali
from app.models import Expense, ExpenseCategory, PaymentKind
from app.repositories.pagination import paginate
from app.services import finance as finance_service

SECTION = "fin"
# A month token before this year is garbage (or tampering), not history.
_MIN_MONTH = (1300, 1)
_EXPENSES_PER_PAGE = 15
_NOTE_IN_LIST = 40  # characters of a note shown in the expense list

_AMOUNT_STEP = "fin:amount"
_CATEGORY_STEP = "fin:cat"
_DATE_STEP = "fin:date"
_NOTE_STEP = "fin:note"

_KIND_LABELS = {
    PaymentKind.TUITION: A.KIND_TUITION,
    PaymentKind.GYM_FEE: A.KIND_GYM_FEE,
    PaymentKind.OTHER: A.KIND_OTHER,
}
_CATEGORY_LABELS = {category: F.CATEGORY_LABELS[category.name] for category in ExpenseCategory}

Month = tuple[int, int]


def handle_callback(req: AdminReq, args: str) -> None:
    action, _, rest = (args or "").partition(":")
    if action == "y":
        _year(req, _month_arg(rest))
    elif action == "x":
        token, _, tail = rest.partition(":")
        _expenses(req, _month_arg(token), page=_page_arg(tail))
    elif action == "new":
        _ask_amount(req, {"origin": rest if _parse_month(rest) else ""})
    elif action == "cat":
        _set_category(req, rest)
    elif action == "today":
        data = _pending(req, _DATE_STEP)
        if data is None:
            _expired(req)
            return
        _after_date(req, data, clock.today())
    elif action == "skip":
        _save(req, note=None)
    else:  # «m», the bare section, and anything unrecognised: a month report
        _report(req, _month_arg(rest if action == "m" else ""))


def handle_message(req: AdminReq, message: dict, substep: str, state) -> None:
    text = (message.get("text") or "").strip()
    data = state.data
    if substep == "amount":
        amount = common.parse_amount(text)
        if amount is None:
            _ask_amount(req, data, warning=A.INVALID_NUMBER)
            return
        try:
            data["amount"] = finance_service.check_amount(amount)
        except ValidationError as exc:
            _ask_amount(req, data, warning=str(exc))
            return
        _ask_category(req, data)
    elif substep == "cat":
        _ask_category(req, data)  # stray text: the category is a tap
    elif substep == "date":
        spent_at = common.parse_date(text)
        if spent_at is None:
            _ask_date(req, data, warning=A.INVALID_DATE)
            return
        _after_date(req, data, spent_at)
    elif substep == "note":
        if not text:  # a photo or a sticker is not a note
            _ask_note(req, data, warning=F.NOTE_NEEDS_TEXT)
            return
        _save(req, note=text)
    else:
        common.clear(req)
        _report(req, finance_service.current_month())


# --- month tokens (tamper-safe) ---


def _token(month: Month) -> str:
    return f"{month[0]:04d}{month[1]:02d}"


def _parse_month(token: str) -> Month | None:
    """A `YYYYMM` Jalali month, or None on anything malformed."""
    if len(token) != 6 or not (token.isascii() and token.isdigit()):
        return None
    month = (int(token[:4]), int(token[4:]))
    if month < _MIN_MONTH or not 1 <= month[1] <= 12:
        return None
    return month


def _month_arg(token: str) -> Month:
    """The month a callback asks for — this month when garbled, and never a later
    one (a report of a month that hasn't happened is not a report)."""
    current = finance_service.current_month()
    month = _parse_month(token)
    return current if month is None or month > current else month


def _page_arg(tail: str) -> int:
    label, _, value = tail.partition(":")
    return (cb.parse_int(value) if label == "page" else None) or 1


# --- screens ---


def _net(amount: int) -> str:
    """Profit is green from zero up; a loss is red."""
    return "🟢" if amount >= 0 else "🔴"


def _month_name(month: Month) -> str:
    return JALALI_MONTHS[month[1] - 1]


def _breakdown(totals: dict, labels: dict) -> list[str]:
    return [
        F.BREAKDOWN_ROW.format(label=labels[key], amount=formatting.money(amount))
        for key, amount in totals.items()
        if amount
    ]


def _report(req: AdminReq, month: Month, flash: str | None = None) -> None:
    """«📊 گزارش مالی — مهر 1405»: income by kind, expenses by category, net."""
    report = finance_service.month_report(req.db, *month)
    count = f"{F.LABEL_PAYMENT_COUNT}: {report.payment_count}"
    if report.correction_count:
        count = f"{count} {F.PAYMENT_CORRECTIONS.format(n=report.correction_count)}"
    lines = [
        F.REPORT_TITLE.format(month=_month_name(month), year=month[0]),
        "",
        f"{F.LABEL_INCOME}: {formatting.money(report.income)}",
        *_breakdown(report.income_by_kind, _KIND_LABELS),
        count,
        "",
        f"{F.LABEL_EXPENSES}: {formatting.money(report.expenses)}",
        *_breakdown(report.expenses_by_category, _CATEGORY_LABELS),
        "",
        f"{_net(report.net)} {F.LABEL_NET}: {formatting.money(report.net)}",
    ]
    body = "\n".join(lines)
    if flash:
        body = f"{flash}\n\n{body}"

    token = _token(month)
    nav = []
    previous = finance_service.shift_month(*month, -1)
    if previous >= _MIN_MONTH:
        nav.append(common.button(F.BTN_PREV_MONTH, SECTION, "m", _token(previous)))
    if month < finance_service.current_month():
        following = finance_service.shift_month(*month, 1)
        nav.append(common.button(F.BTN_NEXT_MONTH, SECTION, "m", _token(following)))
    rows = [
        nav,
        [
            common.button(F.BTN_YEAR_SUMMARY, SECTION, "y", token),
            common.button(F.BTN_MONTH_EXPENSES, SECTION, "x", token),
        ],
        [common.button(F.BTN_NEW_EXPENSE, SECTION, "new", token)],
    ]
    common.render(req, body, common.with_back([row for row in rows if row], ("pay",)))


def _year(req: AdminReq, month: Month) -> None:
    """The year of `month` as twelve rows; tap a month (up to this one) to open it."""
    jy = month[0]
    totals = finance_service.year_overview(req.db, jy)
    lines = [F.YEAR_TITLE.format(year=jy), F.YEAR_HINT, ""]
    # A table of bare figures — the hint line says they are Toman — so a row
    # still fits on one phone line.
    for row in totals:
        name = JALALI_MONTHS[row.jm - 1]
        if row.income or row.expenses:
            lines.append(F.YEAR_ROW.format(
                month=name, income=f"{row.income:,}", expenses=f"{row.expenses:,}",
                net=f"{_net(row.net)} {row.net:,}",
            ))
        else:
            lines.append(F.YEAR_ROW_EMPTY.format(month=name))
    income = sum(row.income for row in totals)
    expenses = sum(row.expenses for row in totals)
    lines += [
        "",
        F.YEAR_TOTAL.format(
            income=f"{income:,}", expenses=f"{expenses:,}",
            net=f"{_net(income - expenses)} {income - expenses:,}",
        ),
        "",
        F.YEAR_PICK_MONTH,
    ]
    current = finance_service.current_month()
    buttons = [
        common.button(JALALI_MONTHS[jm - 1], SECTION, "m", _token((jy, jm)))
        for jm in range(1, 13)
        if (jy, jm) <= current
    ]
    rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    common.render(req, "\n".join(lines), common.with_back(rows, (SECTION, "m", _token(month))))


def _expense_line(expense: Expense) -> str:
    line = F.EXPENSE_ROW.format(
        date=format_jalali(expense.spent_at),
        category=_CATEGORY_LABELS[expense.category],
        amount=formatting.money(expense.amount),
    )
    note = " ".join((expense.note or "").split())
    if note:
        line = f"{line} — {note if len(note) <= _NOTE_IN_LIST else note[:_NOTE_IN_LIST] + '…'}"
    return line


def _expenses(req: AdminReq, month: Month, page: int = 1) -> None:
    """«🧾 هزینه‌های مهر 1405» — newest first, a page at a time."""
    token = _token(month)
    report = finance_service.month_report(req.db, *month)
    pages = max((report.expense_count + _EXPENSES_PER_PAGE - 1) // _EXPENSES_PER_PAGE, 1)
    # A stale or tampered page number lands on the last page — and never reaches
    # the database as an offset too large for it.
    result = paginate(
        req.db, finance_service.expenses_stmt(*month), page=min(page, pages),
        per_page=_EXPENSES_PER_PAGE,
    )
    lines = [F.EXPENSES_TITLE.format(month=_month_name(month), year=month[0]), ""]
    if result.total:
        lines.append(F.EXPENSES_TOTAL.format(
            amount=formatting.money(report.expenses), n=report.expense_count
        ))
        lines.append("")
        lines += [_expense_line(expense) for expense in result.items]
    else:
        lines.append(F.EXPENSES_EMPTY)
    rows = [[common.button(F.BTN_NEW_EXPENSE, SECTION, "new", token)]]
    common.render(req, "\n".join(lines), common.pager(
        rows, result.page, result.pages, (SECTION, "x", token), back_parts=(SECTION, "m", token)
    ))


# --- recording an expense: amount → category → date → note ---


def _pending(req: AdminReq, step: str) -> dict | None:
    """The in-progress data, if the chat is still at `step` — a tap on an older
    prompt's button is not."""
    state = req.store.get(req.ctx.platform, req.chat_id)
    return state.data if state is not None and state.step == step else None


def _expired(req: AdminReq) -> None:
    """Where a tap lands once its step is gone (a restart, a double tap, an old message)."""
    common.render(req, F.STEP_EXPIRED, common.with_back([
        [common.button(F.BTN_NEW_EXPENSE, SECTION, "new")],
        [common.button(F.BTN_MONTH_REPORT, SECTION, "m")],
    ], ("pay",)))


def _cancel(data: dict, rows: list | None = None) -> dict:
    """«✖️ لغو» back to the month the entry started from, else the payments page."""
    origin = _parse_month(data.get("origin") or "")
    parts = (SECTION, "m", _token(origin)) if origin else ("pay",)
    return common.cancel_keyboard(parts, rows=rows)


def _ask(warning: str | None, text: str) -> str:
    return f"{warning}\n{text}" if warning else text


def _ask_amount(req: AdminReq, data: dict, warning: str | None = None) -> None:
    common.prompt(req, _ask(warning, F.ASK_AMOUNT), _AMOUNT_STEP, data, keyboard=_cancel(data))


def _ask_category(req: AdminReq, data: dict) -> None:
    cells = [
        common.button(_CATEGORY_LABELS[category], SECTION, "cat", category.name)
        for category in ExpenseCategory
    ]
    common.prompt(
        req, F.ASK_CATEGORY.format(amount=formatting.money(data["amount"])), _CATEGORY_STEP, data,
        keyboard=_cancel(data, rows=[cells[i:i + 2] for i in range(0, len(cells), 2)]),
    )


def _set_category(req: AdminReq, name: str) -> None:
    data = _pending(req, _CATEGORY_STEP)
    if data is None:
        _expired(req)
        return
    if name not in ExpenseCategory.__members__:  # tampered: ask again
        _ask_category(req, data)
        return
    data["category"] = name
    _ask_date(req, data)


def _ask_date(req: AdminReq, data: dict, warning: str | None = None) -> None:
    """The date, with «📅 امروز» one tap away — a typed Jalali date is where a
    wrong year slips in."""
    today = F.BTN_TODAY.format(date=format_jalali(clock.today()))
    common.prompt(
        req, _ask(warning, F.ASK_DATE), _DATE_STEP, data,
        keyboard=_cancel(data, rows=[[common.button(today, SECTION, "today")]]),
    )


def _after_date(req: AdminReq, data: dict, spent_at: date) -> None:
    try:
        data["spent_at"] = finance_service.check_spent_at(spent_at).isoformat()
    except ValidationError as exc:
        _ask_date(req, data, warning=str(exc))
        return
    _ask_note(req, data)


def _ask_note(req: AdminReq, data: dict, warning: str | None = None) -> None:
    common.prompt(
        req, _ask(warning, F.ASK_NOTE), _NOTE_STEP, data,
        keyboard=_cancel(data, rows=[[common.button(A.SKIP, SECTION, "skip")]]),
    )


def _save(req: AdminReq, note: str | None) -> None:
    """Append the expense, then land on its month's report with a flash line."""
    data = _pending(req, _NOTE_STEP)
    if data is None or not {"amount", "category", "spent_at"} <= data.keys():
        _expired(req)  # also what a second tap on «⏭ رد کردن» finds
        return
    try:
        expense = finance_service.record_expense(
            req.db,
            amount=data["amount"],
            category=ExpenseCategory[data["category"]],
            spent_at=date.fromisoformat(data["spent_at"]),
            note=note,
            created_by=req.user_id,
        )
    except ValidationError as exc:  # the prompt sat open until the date aged out
        _ask_date(req, data, warning=str(exc))
        return
    common.clear(req)
    saved = F.EXPENSE_SAVED if expense.amount > 0 else F.CORRECTION_SAVED
    flash = saved.format(
        category=_CATEGORY_LABELS[expense.category], amount=formatting.money(expense.amount)
    )
    _report(req, finance_service.month_of(expense.spent_at), flash=flash)
