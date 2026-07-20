"""Admin section: class-type catalog (list, create, edit, delete, enable/disable)."""

from __future__ import annotations

from app.admin import common
from app.admin.common import AdminReq
from app.copy import admin_texts as A
from app.core.exceptions import DomainError
from app.services import classes as classes_service


def handle_callback(req: AdminReq, args: str) -> None:
    action, _, rest = (args or "").partition(":")
    if action == "new":
        common.prompt(req, A.ASK_CLASS_TITLE, "classes:new_title", {})
    elif action == "toggle" and rest.isdigit():
        class_type = classes_service.get(req.db, int(rest))
        classes_service.set_active(req.db, class_type.id, not class_type.active)
        _list(req)
    elif action == "edit" and rest.isdigit():
        class_type = classes_service.get(req.db, int(rest))
        common.prompt(
            req, f"عنوان فعلی: {class_type.title}\n\n{A.ASK_CLASS_TITLE}",
            f"classes:edit:{class_type.id}", {},
        )
    elif action == "delete" and rest.isdigit():
        try:
            classes_service.delete(req.db, int(rest))
        except DomainError as exc:
            common.send(req, str(exc))
        _list(req)
    else:
        _list(req)


def handle_message(req: AdminReq, message: dict, substep: str, state) -> None:
    text = (message.get("text") or "").strip()
    action, _, id_str = substep.partition(":")
    if substep == "new_title":
        if not text:
            common.prompt(req, A.ASK_CLASS_TITLE, "classes:new_title", {})
            return
        classes_service.create(req.db, title=text)
        common.clear(req)
        _list(req)
    elif action == "edit" and id_str.isdigit():
        if not text:
            common.prompt(req, A.ASK_CLASS_TITLE, substep, {})
            return
        classes_service.update(req.db, int(id_str), title=text)
        common.clear(req)
        _list(req)
    else:
        common.clear(req)
        _list(req)


def _list(req: AdminReq) -> None:
    items = classes_service.list_class_types(req.db)
    rows = [[common.button(A.BTN_NEW_CLASS, "classes", "new")]]
    for c in items:
        rows.append([
            common.button(f"{'🟢' if c.active else '⚪'} {c.title}", "classes", "toggle", c.id),
            common.button("✏️", "classes", "edit", c.id),
            common.button("🗑", "classes", "delete", c.id),
        ])
    common.render(req, f"{A.CLASSES_TITLE}\n{A.CLASSES_HINT}", common.with_back(rows))
