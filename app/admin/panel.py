"""In-bot admin panel entry point + section dispatch (shared by Telegram & Bale).

Authorization is enforced by the router BEFORE anything here runs (numeric owner
whitelist / DB role). This module routes ``a:<section>:...`` callbacks and
active-flow text/file messages to the section handlers; all real work goes
through the shared service layer, so both bots behave identically.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.admin import attendance as attendance_admin
from app.admin import classes as classes_admin
from app.admin import courses as courses_admin
from app.admin import notifications as notifications_admin
from app.admin import payments as payments_admin
from app.admin import programs as programs_admin
from app.admin import settings as settings_admin
from app.admin import start as start_admin
from app.admin import students as students_admin
from app.admin.common import AdminReq
from app.bots.common import keyboards
from app.bots.common.context import BotContext
from app.bots.common.state import ChatState, StateStore
from app.copy import texts
from app.core.exceptions import DomainError
from app.models import Person

logger = logging.getLogger(__name__)

SECTIONS = {
    "students": students_admin,
    "classes": classes_admin,
    "courses": courses_admin,
    "attend": attendance_admin,
    "plans": programs_admin,
    "pay": payments_admin,
    "notify": notifications_admin,
    "settings": settings_admin,
    "start": start_admin,
}


def open_panel(
    ctx: BotContext,
    db: Session,
    chat_id: object,
    message_id: int | None,
    user_id: str,
    store: StateStore | None = None,
) -> None:
    if store is not None:
        store.clear(ctx.platform, chat_id)
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
    section, _, args = (rest or "").partition(":")
    if section in ("", "home"):
        open_panel(ctx, db, chat_id, message_id, user_id, store)
        return
    module = SECTIONS.get(section)
    if module is None:
        open_panel(ctx, db, chat_id, message_id, user_id, store)
        return
    req = AdminReq(ctx, db, chat_id, message_id, user_id, person, store)
    try:
        module.handle_callback(req, args)
    except DomainError as exc:
        ctx.send(chat_id, str(exc))


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
    section, _, substep = (state.step or "").partition(":")
    module = SECTIONS.get(section)
    if module is None:
        store.clear(ctx.platform, chat_id)
        open_panel(ctx, db, chat_id, None, user_id, store)
        return
    # Fresh sends during a flow (message_id=None) so we never edit the user's msg.
    req = AdminReq(ctx, db, chat_id, None, user_id, person, store)
    try:
        module.handle_message(req, message, substep, state)
    except DomainError as exc:
        ctx.send(chat_id, str(exc))
