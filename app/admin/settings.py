"""Admin section: edit application settings (messages, card number, thresholds…)."""

from __future__ import annotations

from app.admin import common
from app.admin.common import AdminReq
from app.copy import admin_texts as A
from app.services import settings as settings_service


def handle_callback(req: AdminReq, args: str) -> None:
    action, _, rest = (args or "").partition(":")
    if action == "edit" and rest in A.SETTINGS_LABELS:
        current = settings_service.get_value(req.db, rest)
        label = A.SETTINGS_LABELS[rest]
        common.prompt(
            req,
            f"{label}\nمقدار فعلی:\n{current or '-'}\n\n{A.ASK_SETTING_VALUE}",
            f"settings:save:{rest}",
            {},
        )
    else:
        _list(req)


def handle_message(req: AdminReq, message: dict, substep: str, state) -> None:
    action, _, key = substep.partition(":")
    if action == "save" and key in A.SETTINGS_LABELS:
        settings_service.set_value(req.db, key, (message.get("text") or "").strip())
        common.clear(req)
        common.send(req, A.SETTING_SAVED)
        _list(req)
    else:
        common.clear(req)
        _list(req)


def _list(req: AdminReq) -> None:
    rows = [
        [common.button(label, "settings", "edit", key)]
        for key, label in A.SETTINGS_LABELS.items()
    ]
    common.render(req, f"{A.SETTINGS_TITLE}\n{A.SETTINGS_HINT}", common.with_back(rows))
