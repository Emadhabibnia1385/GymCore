"""In-bot admin panel entry point (shared by Telegram and Bale).

Authorization is enforced by the router BEFORE any function here runs (numeric
owner whitelist / DB role). The concrete management sections (students, classes,
courses, attendance, plans, payments, notifications, settings) are implemented
in Phase 5+; this module owns the panel entry and section dispatch.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.bots.common import keyboards
from app.bots.common.context import BotContext
from app.bots.common.state import ChatState, StateStore
from app.copy import texts
from app.models import Person

logger = logging.getLogger(__name__)

_UNDER_CONSTRUCTION = "این بخش به‌زودی کامل می‌شود 🟢"


def open_panel(
    ctx: BotContext, db: Session, chat_id: object, message_id: int | None, user_id: str
) -> None:
    ctx.show(
        chat_id,
        f"{texts.ADMIN_TITLE}\n\n{texts.ADMIN_WELCOME}",
        keyboards.admin_menu(),
        message_id,
    )


def handle_callback(
    ctx: BotContext,
    db: Session,
    chat_id: object,
    message_id: int | None,
    rest: str | None,
    user_id: str,
    person: Person,
    store: StateStore,
) -> None:
    """Dispatch an ``a:*`` admin callback. rest is everything after ``a:``."""
    section, _, _ = (rest or "").partition(":")
    if section in ("", "home"):
        open_panel(ctx, db, chat_id, message_id, user_id)
        return
    # Placeholder until Phase 5 wires each section's handlers.
    ctx.show(chat_id, _UNDER_CONSTRUCTION, keyboards.admin_menu(), message_id)


def handle_message(
    ctx: BotContext,
    db: Session,
    chat_id: object,
    message: dict,
    state: ChatState,
    user_id: str,
    person: Person,
    store: StateStore,
) -> None:
    """Handle a text/file message that belongs to an active admin flow (Phase 5)."""
    store.clear(ctx.platform, chat_id)
    open_panel(ctx, db, chat_id, None, user_id)
