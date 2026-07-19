"""Admin section: payment recording (immutable) + balances + history."""

from __future__ import annotations

from datetime import date

from app.admin import common
from app.admin.common import AdminReq
from app.bots.common import formatting
from app.copy import admin_texts as A
from app.core.jalali import format_jalali
from app.models import PaymentKind
from app.services import courses as courses_service
from app.services import payments as payments_service
from app.services import persons as persons_service

_KIND_LABELS = {
    "TUITION": A.KIND_TUITION,
    "GYM_FEE": A.KIND_GYM_FEE,
    "OTHER": A.KIND_OTHER,
}


def handle_callback(req: AdminReq, args: str) -> None:
    action, _, rest = (args or "").partition(":")
    if action == "client" and rest.isdigit():
        _client(req, int(rest))
    elif action == "course" and rest.isdigit():
        _course(req, int(rest))
    elif action == "new":
        client_id, _, course_id = rest.partition(":")
        if client_id.isdigit():
            course = int(course_id) if course_id.isdigit() and course_id != "0" else None
            common.prompt(req, A.ASK_PAYMENT_AMOUNT, "pay:amount",
                          {"client_id": int(client_id), "course_id": course})
    elif action == "kind":
        _set_kind(req, rest)
    elif action == "note_skip":
        _save(req, note=None)
    else:
        common.render(req, A.PAYMENTS_TITLE, common.with_back([]))


def handle_message(req: AdminReq, message: dict, substep: str, state) -> None:
    text = (message.get("text") or "").strip()
    data = state.data
    if substep == "amount":
        amount = common.parse_amount(text)
        if amount is None or amount == 0:
            common.prompt(req, f"{A.INVALID_NUMBER}\n{A.ASK_PAYMENT_AMOUNT}", "pay:amount", data)
            return
        data["amount"] = amount
        common.prompt(req, A.ASK_PAYMENT_DATE, "pay:date", data)
    elif substep == "date":
        paid_at = common.parse_date(text)
        if paid_at is None:
            common.prompt(req, A.INVALID_DATE, "pay:date", data)
            return
        data["date"] = paid_at.isoformat()
        common.prompt(req, A.ASK_PAYMENT_KIND, "pay:kind_wait", data, keyboard=_kind_keyboard())
    elif substep == "note":
        _save(req, note=text or None)
    else:
        common.clear(req)


def _kind_keyboard() -> dict:
    rows = [[common.button(label, "pay", "kind", name)] for name, label in _KIND_LABELS.items()]
    return common.inline(rows + [[common.home_button()]])


def _set_kind(req: AdminReq, kind_name: str) -> None:
    state = req.store.get(req.ctx.platform, req.chat_id)
    if state is None or kind_name not in PaymentKind.__members__:
        common.render(req, A.PAYMENTS_TITLE, common.with_back([]))
        return
    state.data["kind"] = kind_name
    common.prompt(req, A.ASK_PAYMENT_NOTE, "pay:note", state.data,
                  keyboard=common.skip_keyboard(("pay", "note_skip")))


def _save(req: AdminReq, note: str | None) -> None:
    state = req.store.get(req.ctx.platform, req.chat_id)
    if state is None or "amount" not in state.data or "kind" not in state.data:
        common.render(req, A.PAYMENTS_TITLE, common.with_back([]))
        return
    data = state.data
    payments_service.record(
        req.db,
        person_id=data["client_id"],
        amount=data["amount"],
        kind=PaymentKind[data["kind"]],
        paid_at=date.fromisoformat(data["date"]),
        course_id=data.get("course_id"),
        note=note,
        created_by=req.user_id,
        notify=True,
    )
    if data.get("course_id"):
        back = ("pay", "course", data["course_id"])
    else:
        back = ("pay", "client", data["client_id"])
    common.clear(req)
    common.render(req, A.PAYMENT_SAVED, common.back_home(*back))


def _client(req: AdminReq, client_id: int) -> None:
    persons_service.get(req.db, client_id)
    courses = courses_service.list_courses(req.db, client_id=client_id)
    rows = [[common.button(c.class_type.title, "pay", "course", c.id)] for c in courses]
    rows.insert(0, [common.button(A.BTN_NEW_PAYMENT, "pay", "new", client_id, 0)])
    total = payments_service.total_paid_person(req.db, client_id)
    body = f"{A.PAYMENTS_TITLE}\n{A.LABEL_PAID}: {formatting.money(total)}"
    common.render(req, body, common.with_back(rows, ("students", "view", client_id)))


def _course(req: AdminReq, course_id: int) -> None:
    course = courses_service.get(req.db, course_id)
    balance = payments_service.course_balance(req.db, course)
    payments = payments_service.list_payments(req.db, course_id=course_id)
    lines = [
        f"💳 {course.class_type.title}",
        f"{A.LABEL_TOTAL_DUE}: {formatting.money(balance['total_due'])}",
        f"{A.LABEL_PAID}: {formatting.money(balance['paid'])}",
        f"{A.LABEL_OUTSTANDING}: 🟢 {formatting.money(balance['outstanding'])}",
    ]
    if payments:
        lines.append("")
        for payment in payments[:10]:
            lines.append(f"• {formatting.money(payment.amount)} — {format_jalali(payment.paid_at)}")
    rows = [[common.button(A.BTN_NEW_PAYMENT, "pay", "new", course.client_id, course.id)]]
    common.render(
        req, "\n".join(lines), common.with_back(rows, ("pay", "client", course.client_id))
    )
