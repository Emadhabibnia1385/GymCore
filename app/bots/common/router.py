"""Update dispatcher shared by both bots.

Parses Telegram/Bale updates and routes them to the client flow or the admin
panel. Admin callbacks are authorization-gated HERE, before any admin handler
runs, so callback tampering by a non-owner is rejected outright.
"""

from __future__ import annotations

import logging

from app.admin import panel as admin_panel
from app.bots.common import callbacks, client_flow
from app.bots.common.context import BotContext
from app.bots.common.state import StateStore
from app.copy import texts
from app.db.session import session_scope
from app.services import auth

logger = logging.getLogger(__name__)


class Dispatcher:
    def __init__(self, ctx: BotContext):
        self.ctx = ctx
        self.store = StateStore()

    def handle_update(self, update: dict) -> None:
        try:
            if "callback_query" in update:
                self._callback(update["callback_query"])
            elif "message" in update:
                self._message(update["message"])
        except Exception:
            logger.exception("Unhandled error dispatching update")
            self._safe_error(update)

    # --- messages ---

    def _message(self, message: dict) -> None:
        chat_id = (message.get("chat") or {}).get("id")
        from_user = message.get("from") or {}
        user_id = str(from_user.get("id"))
        text = (message.get("text") or "").strip()
        incoming_id = message.get("message_id")
        try:
            with session_scope() as db:
                # Registration gate: collect a phone on first contact (owners bypass).
                person = client_flow.resolve_registered(self.ctx, db, chat_id, from_user, message)
                if person is None:
                    return  # awaiting phone
                state = self.store.get(self.ctx.platform, chat_id)
                if state is not None and state.flow == "admin":
                    if auth.is_admin(db, self.ctx.platform, user_id):
                        admin_panel.handle_message(
                            self.ctx, db, chat_id, message, state, user_id, person, self.store
                        )
                    else:
                        self.store.clear(self.ctx.platform, chat_id)
                    return
                client_flow.show_menu(
                    self.ctx, db, chat_id, user_id, person, greet=(text == "/start" or not text)
                )
        finally:
            # Single-message UX: remove the user's own message from the chat.
            if incoming_id is not None:
                self.ctx.delete(chat_id, incoming_id)

    # --- callbacks ---

    def _callback(self, callback_query: dict) -> None:
        data = callback_query.get("data") or ""
        callback_id = callback_query.get("id")
        message = callback_query.get("message") or {}
        chat_id = (message.get("chat") or {}).get("id")
        message_id = message.get("message_id")
        from_user = callback_query.get("from") or {}
        user_id = str(from_user.get("id"))
        action, rest = callbacks.parse(data)

        with session_scope() as db:
            person = client_flow.provision_for_callback(self.ctx, db, from_user)
            if person is None:  # not registered yet — must /start and share a phone
                self.ctx.answer(callback_id, texts.NEED_PHONE, alert=True)
                return

            if action in (callbacks.ADMIN_PREFIX, callbacks.ADMIN):
                if not auth.is_admin(db, self.ctx.platform, user_id):
                    self.ctx.answer(callback_id, texts.ACCESS_DENIED, alert=True)
                    return
                self.ctx.answer(callback_id)
                if action == callbacks.ADMIN:
                    admin_panel.open_panel(self.ctx, db, chat_id, message_id, user_id, self.store)
                else:
                    admin_panel.handle_callback(
                        self.ctx, db, chat_id, message_id, rest, user_id, person, self.store
                    )
                return

            self.ctx.answer(callback_id)
            client_flow.route(
                self.ctx, db, chat_id, user_id, person, message_id, action, rest
            )

    def _safe_error(self, update: dict) -> None:
        message = update.get("message") or (update.get("callback_query") or {}).get("message") or {}
        chat_id = (message.get("chat") or {}).get("id")
        if chat_id is None:
            return
        try:
            self.ctx.send(chat_id, texts.ERROR)
        except Exception:
            logger.debug("failed to send error notice")
