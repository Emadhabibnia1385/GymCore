"""Admin section: the coach's contact links (text, address, order, on/off).

What the client sees under «راه‌های ارتباطی ما» lives in the database, so the
coach can change a phone number or a handle from inside the bot instead of
needing a code change. Each link opens its own small hub, mirroring the
student-profile design.
"""

from __future__ import annotations

from app.admin import common
from app.admin.common import AdminReq
from app.copy import admin_texts as A
from app.services import contact_links as links_service


def handle_callback(req: AdminReq, args: str) -> None:
    action, _, rest = (args or "").partition(":")
    if action == "view" and rest.isdigit():
        _view(req, int(rest))
    elif action == "toggle" and rest.isdigit():
        link = links_service.get(req.db, int(rest))
        links_service.set_active(req.db, link.id, not link.active)
        _view(req, link.id)
    elif action == "label" and rest.isdigit():
        link = links_service.get(req.db, int(rest))
        common.prompt(
            req, A.ASK_LINK_LABEL.format(current=link.label), f"contacts:label:{link.id}", {}
        )
    elif action == "url" and rest.isdigit():
        link = links_service.get(req.db, int(rest))
        common.prompt(
            req, A.ASK_LINK_URL.format(current=link.url), f"contacts:url:{link.id}", {}
        )
    elif action in ("up", "down") and rest.isdigit():
        links_service.move(req.db, int(rest), -1 if action == "up" else 1)
        _list(req)
    else:
        _list(req)


def handle_message(req: AdminReq, message: dict, substep: str, state) -> None:
    text = (message.get("text") or "").strip()
    field, _, id_str = substep.partition(":")
    if field in ("label", "url") and id_str.isdigit():
        if not text:
            link = links_service.get(req.db, int(id_str))
            current = link.label if field == "label" else link.url
            prompt = A.ASK_LINK_LABEL if field == "label" else A.ASK_LINK_URL
            common.prompt(req, prompt.format(current=current), substep, {})
            return
        links_service.update(req.db, int(id_str), **{field: text})
        common.clear(req)
        _view(req, int(id_str), flash=A.LINK_SAVED)
    else:
        common.clear(req)
        _list(req)


def _list(req: AdminReq) -> None:
    """Every link in display order — tap one to edit it."""
    rows = [
        [common.button(
            f"{'🟢' if link.active else '⚪'} {link.icon or ''} {link.label}".strip(),
            "contacts", "view", link.id,
        )]
        for link in links_service.list_all(req.db)
    ]
    body = f"{A.CONTACTS_TITLE}\n{A.CONTACTS_HINT}"
    common.render(req, body, common.with_back(rows))


def _view(req: AdminReq, link_id: int, flash: str | None = None) -> None:
    link = links_service.get(req.db, link_id)
    lines = [
        f"{link.icon or '🔗'} {link.label}",
        f"{A.LABEL_LINK_URL}: {link.url}",
        f"{A.LABEL_STATUS}: {A.LABEL_ACTIVE if link.active else A.LABEL_INACTIVE}",
    ]
    if flash:
        lines.insert(0, f"{flash}\n")
    rows = [
        [
            common.button(A.BTN_EDIT_LINK_LABEL, "contacts", "label", link.id),
            common.button(A.BTN_EDIT_LINK_URL, "contacts", "url", link.id),
        ],
        [
            common.button(
                A.BTN_LINK_OFF if link.active else A.BTN_LINK_ON, "contacts", "toggle", link.id
            )
        ],
        [
            common.button(A.BTN_MOVE_UP, "contacts", "up", link.id),
            common.button(A.BTN_MOVE_DOWN, "contacts", "down", link.id),
        ],
    ]
    common.render(req, "\n".join(lines), common.with_back(rows, ("contacts",)))
