"""Shared framework for the in-bot admin panel.

Every section uses AdminReq (the per-update bundle), the render/send helpers,
the conversation-state helpers, and the pagination keyboard builder. Section
handlers stay thin; all real work goes through the service layer.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.bots.common import callbacks as cb
from app.bots.common.context import BotContext
from app.bots.common.state import ChatState, StateStore
from app.copy import admin_texts as A
from app.core.jalali import parse_jalali
from app.models import Person


@dataclass
class AdminReq:
    ctx: BotContext
    db: Session
    chat_id: object
    message_id: int | None
    user_id: str
    person: Person
    store: StateStore


# --- rendering ---


def render(req: AdminReq, text: str, keyboard: dict | None = None) -> None:
    """Render a screen in place (or fresh on Bale) — clears any pending state."""
    req.store.clear(req.ctx.platform, req.chat_id)
    req.ctx.show(req.chat_id, text, keyboard, req.message_id)


def send(req: AdminReq, text: str, keyboard: dict | None = None) -> None:
    req.ctx.send(req.chat_id, text, keyboard)


def prompt(req: AdminReq, text: str, step: str, data: dict | None = None,
           keyboard: dict | None = None) -> None:
    """Ask for text/file input: store the next step, then send the prompt fresh."""
    state = ChatState(flow="admin", step=step, data=data or {})
    req.store.set(req.ctx.platform, req.chat_id, state)
    req.ctx.send(req.chat_id, text, keyboard)


def clear(req: AdminReq) -> None:
    req.store.clear(req.ctx.platform, req.chat_id)


# --- keyboards ---


_STYLE_DANGER = "danger"  # red — for back/home navigation buttons (stripped on Bale)


def button(text: str, *parts: object, style: str | None = None) -> dict:
    btn = {"text": text, "callback_data": cb.admin(*parts)}
    if style:
        btn["style"] = style
    return btn


def home_button() -> dict:
    return button(A.BACK, "home", style=_STYLE_DANGER)


def _back_button(back_parts: tuple) -> dict:
    return button(A.BACK, *back_parts, style=_STYLE_DANGER)


def inline(rows: list[list[dict]]) -> dict:
    return {"inline_keyboard": rows}


def with_back(rows: list[list[dict]], back_parts: tuple | None = None) -> dict:
    back = _back_button(back_parts) if back_parts else home_button()
    return inline([*rows, [back]])


def back_home(*back_parts: object) -> dict:
    """A two-row nav keyboard: a contextual back button + the admin-home button."""
    if back_parts:
        return inline([[_back_button(back_parts)], [home_button()]])
    return inline([[home_button()]])


def pager(
    rows: list[list[dict]],
    page: int,
    pages: int,
    base_parts: tuple,
    back_parts: tuple | None = None,
) -> dict:
    """Append prev/next navigation + a back button to a list of item rows."""
    nav: list[dict] = []
    if page > 1:
        nav.append(button(A.PREV, *base_parts, "page", page - 1))
    if page < pages:
        nav.append(button(A.NEXT, *base_parts, "page", page + 1))
    all_rows = list(rows)
    if nav:
        all_rows.append(nav)
    back = _back_button(back_parts) if back_parts else home_button()
    all_rows.append([back])
    return inline(all_rows)


def confirm_keyboard(confirm_parts: tuple, cancel_parts: tuple = ("home",)) -> dict:
    return inline(
        [[button(A.CONFIRM, *confirm_parts), button(A.CANCEL, *cancel_parts)]]
    )


def skip_keyboard(skip_parts: tuple) -> dict:
    return inline([[button(A.SKIP, *skip_parts)], [home_button()]])


# --- parsing ---


def parse_amount(text: str) -> int | None:
    """Parse a (possibly negative) integer Toman amount from user text."""
    cleaned = (text or "").strip().translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    cleaned = cleaned.replace(",", "").replace("٬", "").replace(" ", "")
    try:
        return int(cleaned)
    except ValueError:
        return None


def parse_count(text: str) -> int | None:
    value = parse_amount(text)
    return value if value is not None and value >= 0 else None


def parse_date(text: str):
    return parse_jalali(text or "")
