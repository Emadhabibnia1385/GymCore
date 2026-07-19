"""Admin section: class-type catalog (list, create, enable/disable)."""

from __future__ import annotations

from app.admin import common
from app.admin.common import AdminReq
from app.copy import admin_texts as A
from app.services import classes as classes_service


def handle_callback(req: AdminReq, args: str) -> None:
    action, _, rest = (args or "").partition(":")
    if action == "new":
        common.prompt(req, A.ASK_CLASS_TITLE, "classes:new_title", {})
    elif action == "toggle" and rest.isdigit():
        class_type = classes_service.get(req.db, int(rest))
        classes_service.set_active(req.db, class_type.id, not class_type.active)
        _list(req)
    else:
        _list(req)


def handle_message(req: AdminReq, message: dict, substep: str, state) -> None:
    text = (message.get("text") or "").strip()
    if substep == "new_title":
        if not text:
            common.prompt(req, A.ASK_CLASS_TITLE, "classes:new_title", {})
            return
        classes_service.create(req.db, title=text)
        common.clear(req)
        _list(req)
    else:
        common.clear(req)
        _list(req)


def _list(req: AdminReq) -> None:
    items = classes_service.list_class_types(req.db)
    rows = [
        [common.button(f"{'🟢' if c.active else '⚪'} {c.title}", "classes", "toggle", c.id)]
        for c in items
    ]
    rows.insert(0, [common.button(A.BTN_NEW_CLASS, "classes", "new")])
    common.render(req, A.CLASSES_TITLE, common.with_back(rows))
