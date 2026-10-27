"""Admin section: edit application settings (messages, card number, thresholds…)."""

from __future__ import annotations

from app.admin import common
from app.admin.common import AdminReq
from app.bots.common import keyboards
from app.copy import admin_texts as A
from app.models.setting import (
    KEY_DEFAULT_ALLOWED_ABSENCE,
    KEY_LOW_SESSION_THRESHOLD,
    KEY_NOTIFY_ON_ATTENDANCE,
    KEY_SIGNUP_URL,
)
from app.services import settings as settings_service

# On/off settings flip in place from the list — nobody should have to type 0 or 1.
_TOGGLES = {KEY_NOTIFY_ON_ATTENDANCE}
# Saved only in the shape their readers expect: a bad number would be ignored
# in silence, and a bad link drops the «سفارش برنامه» button from the menu.
_NUMBERS = {KEY_DEFAULT_ALLOWED_ABSENCE, KEY_LOW_SESSION_THRESHOLD}
_LINKS = {KEY_SIGNUP_URL}


def handle_callback(req: AdminReq, args: str) -> None:
    action, _, rest = (args or "").partition(":")
    if action == "toggle" and rest in _TOGGLES:
        enabled = settings_service.get_bool(req.db, rest)
        settings_service.set_value(req.db, rest, "0" if enabled else "1")
        _list(req, flash=A.SETTING_SAVED)
    elif action == "edit" and rest in A.SETTINGS_LABELS and rest not in _TOGGLES:
        _ask(req, rest)
    else:
        _list(req)


def handle_message(req: AdminReq, message: dict, substep: str, state) -> None:
    action, _, key = substep.partition(":")
    if action != "save" or key not in A.SETTINGS_LABELS or key in _TOGGLES:
        common.clear(req)
        _list(req)
        return
    value = (message.get("text") or "").strip()
    if not value:  # a photo or a sticker must not wipe the setting
        _ask(req, key, warning=A.SETTING_NEEDS_TEXT)
        return
    if key in _NUMBERS:
        number = common.parse_count(value)
        if number is None:
            _ask(req, key, warning=A.SETTING_NEEDS_NUMBER)
            return
        value = str(number)
    if key in _LINKS and not keyboards.is_button_url(value):
        _ask(req, key, warning=A.SETTING_NEEDS_LINK)
        return
    settings_service.set_value(req.db, key, value)
    common.clear(req)
    _list(req, flash=A.SETTING_SAVED)


def _ask(req: AdminReq, key: str, warning: str | None = None) -> None:
    current = settings_service.get_value(req.db, key)
    text = f"{A.SETTINGS_LABELS[key]}\nمقدار فعلی:\n{current or '-'}\n\n{A.ASK_SETTING_VALUE}"
    if warning:
        text = f"{warning}\n\n{text}"
    common.prompt(
        req, text, f"settings:save:{key}", {}, keyboard=common.cancel_keyboard(("settings",))
    )


def _list(req: AdminReq, flash: str | None = None) -> None:
    rows = []
    for key, label in A.SETTINGS_LABELS.items():
        if key in _TOGGLES:
            template = A.SETTING_ON if settings_service.get_bool(req.db, key) else A.SETTING_OFF
            rows.append([common.button(template.format(label=label), "settings", "toggle", key)])
        else:
            rows.append([common.button(label, "settings", "edit", key)])
    body = f"{A.SETTINGS_TITLE}\n{A.SETTINGS_HINT}"
    common.render(req, f"{flash}\n\n{body}" if flash else body, common.with_back(rows))
