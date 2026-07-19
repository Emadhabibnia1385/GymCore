"""Admin section: notifications (manual broadcast, low-session reminders)."""

from __future__ import annotations

from sqlalchemy import select

from app.admin import common
from app.admin.common import AdminReq
from app.copy import admin_texts as A
from app.models import (
    CourseStatus,
    Notification,
    NotificationKind,
    NotificationStatus,
    Person,
    Role,
)
from app.models.setting import KEY_LOW_SESSION_THRESHOLD
from app.services import courses as courses_service
from app.services import notifications as notify_service
from app.services import settings as settings_service


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
        recipients = _active_clients(req.db)
        common.prompt(
            req,
            A.BROADCAST_CONFIRM.format(count=len(recipients)),
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


def _active_clients(db) -> list[Person]:
    return list(
        db.scalars(
            select(Person).where(Person.role == Role.CLIENT, Person.is_active.is_(True))
        )
    )


def _send_broadcast(req: AdminReq) -> None:
    state = req.store.get(req.ctx.platform, req.chat_id)
    if state is None or not state.data.get("text"):
        _menu(req)
        return
    text = state.data["text"]
    count = 0
    for client in _active_clients(req.db):
        if notify_service.person_targets(client):
            notify_service.notify_person(req.db, client, text)
            count += 1
    req.db.add(
        Notification(
            kind=NotificationKind.BROADCAST,
            body=text,
            status=NotificationStatus.SENT,
            created_by=req.user_id,
        )
    )
    req.db.commit()
    common.clear(req)
    common.render(req, A.BROADCAST_QUEUED.format(count=count), common.with_back([]))


def _low_sessions(req: AdminReq) -> None:
    threshold = settings_service.get_int(req.db, KEY_LOW_SESSION_THRESHOLD, 2)
    count = 0
    for course in courses_service.list_courses(req.db, status=CourseStatus.ACTIVE):
        remaining = courses_service.remaining_sessions(req.db, course)
        if remaining <= threshold:
            notify_service.notify_person(
                req.db,
                course.client,
                f"⚠️ فقط {remaining} جلسه از دوره‌ات باقی مانده است.\n"
                "برای تمدید با مربی هماهنگ کن 🟢",
            )
            count += 1
    common.render(req, A.LOW_SESSIONS_DONE.format(count=count), common.with_back([]))
