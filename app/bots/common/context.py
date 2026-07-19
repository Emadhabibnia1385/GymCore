"""Platform-aware wrapper around a BotClient.

Handlers are written once against BotContext; the context knows each platform's
capabilities and quirks:

- Telegram supports Web Apps (Mini App) and reliable inline-message editing.
- Bale does NOT support Web Apps, and editing a message that carries an inline
  keyboard is unreliable — so on Bale we send a fresh message for detail views
  instead of editing in place.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.bots.common.client import BotApiError, BotClient
from app.models import Platform

logger = logging.getLogger(__name__)


@dataclass
class BotContext:
    client: BotClient
    platform: Platform
    supports_web_app: bool
    supports_edit: bool

    # --- primitives ---

    def send(self, chat_id: int | str, text: str, keyboard: dict | None = None) -> dict:
        return self.client.send_message(chat_id, text, reply_markup=keyboard)

    def answer(self, callback_query_id: str, text: str | None = None, alert: bool = False) -> None:
        try:
            self.client.answer_callback_query(callback_query_id, text=text, show_alert=alert)
        except BotApiError:
            logger.debug("answerCallbackQuery failed (non-fatal)")

    def show(
        self,
        chat_id: int | str,
        text: str,
        keyboard: dict | None = None,
        message_id: int | None = None,
    ) -> dict:
        """Render a screen: edit in place where reliable, else send fresh.

        Falling back to a fresh send keeps navigation working on Bale and when
        the original message can't be edited (e.g. it was a document).
        """
        if message_id is not None and self.supports_edit:
            try:
                return self.client.edit_message_text(
                    chat_id, message_id, text, reply_markup=keyboard
                )
            except BotApiError:
                pass
        return self.send(chat_id, text, keyboard)


def make_context(client: BotClient) -> BotContext:
    """Build a BotContext with the right capabilities for the client's platform."""
    if client.platform == Platform.TELEGRAM:
        return BotContext(
            client=client, platform=Platform.TELEGRAM, supports_web_app=True, supports_edit=True
        )
    # Bale (and any other Telegram-compatible platform) — conservative defaults.
    return BotContext(
        client=client, platform=client.platform, supports_web_app=False, supports_edit=False
    )
