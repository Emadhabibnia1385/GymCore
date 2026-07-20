"""Admin section: the start menu's text (main intro) and poster image.

The poster is stored per platform as a photo file_id (Telegram/Bale file_ids are
not interchangeable), so a Telegram admin sets the Telegram poster and vice-versa.
"""

from __future__ import annotations

from app.admin import common
from app.admin.common import AdminReq
from app.copy import admin_texts as A
from app.models.setting import KEY_MAIN_INTRO
from app.services import settings as settings_service


def _poster_key(req: AdminReq) -> str:
    return settings_service.start_poster_key(req.ctx.platform)


def handle_callback(req: AdminReq, args: str) -> None:
    action, _, _rest = (args or "").partition(":")
    if action == "text":
        current = settings_service.get_value(req.db, KEY_MAIN_INTRO)
        common.prompt(req, f"متن فعلی:\n{current}\n\n{A.ASK_START_TEXT}", "start:save_text", {})
    elif action == "poster":
        common.prompt(req, A.ASK_POSTER, "start:poster", {})
    elif action == "poster_clear":
        settings_service.set_value(req.db, _poster_key(req), "")
        common.send(req, A.POSTER_CLEARED)
        _menu(req)
    else:
        _menu(req)


def handle_message(req: AdminReq, message: dict, substep: str, state) -> None:
    if substep == "save_text":
        text = (message.get("text") or "").strip()
        if text:
            settings_service.set_value(req.db, KEY_MAIN_INTRO, text)
            common.send(req, A.START_TEXT_SAVED)
        common.clear(req)
        _menu(req)
    elif substep == "poster":
        photos = message.get("photo")
        if photos:
            file_id = photos[-1].get("file_id")
            settings_service.set_value(req.db, _poster_key(req), file_id)
            common.send(req, A.POSTER_SAVED)
        else:
            common.send(req, A.NOT_A_PHOTO)
        common.clear(req)
        _menu(req)
    else:
        common.clear(req)
        _menu(req)


def _menu(req: AdminReq) -> None:
    has_poster = bool(settings_service.get_value(req.db, _poster_key(req)))
    rows = [
        [common.button(A.BTN_EDIT_START_TEXT, "start", "text")],
        [common.button(A.BTN_SET_POSTER, "start", "poster")],
    ]
    if has_poster:
        rows.append([common.button(A.BTN_CLEAR_POSTER, "start", "poster_clear")])
    common.render(req, f"{A.START_TITLE}\n{A.START_HINT}", common.with_back(rows))
