"""Admin section: notifications (manual broadcast, low-session reminders).

Both actions go through the tracked notification service (queue → dispatch), so
delivery is de-duplicated, retryable and auditable in the notifications table.
"""

from __future__ import annotations

from sqlalchemy import select

from app.admin import common
from app.admin.common import AdminReq
from app.copy import admin_texts as A
from app.models import Person, Role
from app.notifications import service as notify_service


def handle_callback(req: AdminReq, args: str) -> None:
    action, _, _rest = (args or "").partition(":")
    if action == "broadcast":
        common.prompt(req, A.ASK_BROADCAST, "notify:broadcast", {})
    elif action == "send":
        _send_broadcast(req)
    elif action == "low":
        _low_sessions(req)
    else:
        _menu(req)


def handle_message(req: AdminReq, message: dict, substep: str, state) -> None:
    text = (message.get("text") or "").strip()
    if substep == "broadcast":
        if not text:
            common.prompt(req, A.ASK_BROADCAST, "notify:broadcast", {})
            return
        recipients = _active_client_count(req.db)
        common.prompt(
            req,
            A.BROADCAST_CONFIRM.format(count=recipients),
            "notify:confirm",
            {"text": text},
            keyboard=common.confirm_keyboard(("notify", "send"), ("notify", "menu")),
        )
    else:
        common.clear(req)


def _menu(req: AdminReq) -> None:
    rows = [
        [common.button(A.BTN_BROADCAST, "notify", "broadcast")],
        [common.button(A.BTN_LOW_SESSIONS, "notify", "low")],
    ]
    common.render(req, A.NOTIFY_TITLE, common.with_back(rows))


def _active_client_count(db) -> int:
    clients = db.scalars(
        select(Person).where(Person.role == Role.CLIENT, Person.is_active.is_(True))
    ).all()
    return sum(1 for c in clients if c.identities)


def _send_broadcast(req: AdminReq) -> None:
    state = req.store.get(req.ctx.platform, req.chat_id)
    if state is None or not state.data.get("text"):
        _menu(req)
        return
    count = notify_service.broadcast(req.db, state.data["text"], created_by=req.user_id)
    notify_service.dispatch_due(req.db)
    common.clear(req)
    common.render(req, A.BROADCAST_QUEUED.format(count=count), common.with_back([]))


def _low_sessions(req: AdminReq) -> None:
    count = notify_service.generate_reminders(req.db)
    notify_service.dispatch_due(req.db)
    common.render(req, A.LOW_SESSIONS_DONE.format(count=count), common.with_back([]))
