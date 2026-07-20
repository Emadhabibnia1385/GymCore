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
from dataclasses import dataclass, field

from app.bots.common.client import BotApiError, BotClient
from app.models import Platform

logger = logging.getLogger(__name__)


@dataclass
class BotContext:
    client: BotClient
    platform: Platform
    supports_web_app: bool
    supports_edit: bool
    # Coloured inline buttons via the Telegram `style` field (Bot API, Feb 2026).
    # Bale doesn't support it yet, so it stays False there (plain buttons).
    supports_button_style: bool = False
    # `copy_text` inline buttons (tap to copy). Telegram supports it; Bale not.
    supports_copy_text: bool = False
    # Single-message UX: the id of the one "screen" message currently shown per
    # chat. Showing a new screen deletes the previous one, so the chat stays clean.
    _screen: dict = field(default_factory=dict)

    # --- primitives ---

    def _prep(self, keyboard: dict | None) -> dict | None:
        """Strip `style` fields on platforms that don't support them (Bale) — the
        buttons stay valid, just uncoloured, instead of being rejected."""
        if keyboard is None or self.supports_button_style:
            return keyboard
        for row in keyboard.get("inline_keyboard", []):
            for btn in row:
                btn.pop("style", None)
        return keyboard

    def _delete_screen(self, chat_id: int | str) -> None:
        message_id = self._screen.pop(str(chat_id), None)
        if message_id is not None:
            try:
                self.client.delete_message(chat_id, message_id)
            except BotApiError:
                pass

    def _track(self, chat_id: int | str, result: object) -> None:
        if isinstance(result, dict) and result.get("message_id"):
            self._screen[str(chat_id)] = result["message_id"]

    def delete(self, chat_id: int | str, message_id: int) -> None:
        """Best-effort delete of any message (e.g. the user's own message)."""
        try:
            self.client.delete_message(chat_id, message_id)
        except BotApiError:
            pass

    def send(
        self, chat_id: int | str, text: str, keyboard: dict | None = None, track: bool = True
    ) -> dict:
        if track:
            self._delete_screen(chat_id)
        result = self.client.send_message(chat_id, text, reply_markup=self._prep(keyboard))
        if track:
            self._track(chat_id, result)
        return result

    def send_photo(
        self,
        chat_id: int | str,
        photo_id: str,
        caption: str = "",
        keyboard: dict | None = None,
        replace_message_id: int | None = None,
    ) -> dict:
        """Send the start-menu poster as a fresh photo, replacing the current screen."""
        self._delete_screen(chat_id)
        result = self.client.send_photo_id(
            chat_id, photo_id, caption=caption[:1024], reply_markup=self._prep(keyboard)
        )
        self._track(chat_id, result)
        return result

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
        """Render the single screen: edit the tracked message in place when reliable,
        otherwise delete it and send a fresh one — so only one message ever remains.
        """
        keyboard = self._prep(keyboard)
        key = str(chat_id)
        tracked = self._screen.get(key)
        if message_id is not None and self.supports_edit and tracked in (None, message_id):
            try:
                result = self.client.edit_message_text(
                    chat_id, message_id, text, reply_markup=keyboard
                )
                self._screen[key] = message_id
                return result
            except BotApiError:
                pass
        self._delete_screen(chat_id)
        result = self.client.send_message(chat_id, text, reply_markup=keyboard)
        self._track(chat_id, result)
        return result


def make_context(client: BotClient) -> BotContext:
    """Build a BotContext with the right capabilities for the client's platform."""
    if client.platform == Platform.TELEGRAM:
        return BotContext(
            client=client,
            platform=Platform.TELEGRAM,
            supports_web_app=True,
            supports_edit=True,
            supports_button_style=True,
            supports_copy_text=True,
        )
    # Bale (and any other Telegram-compatible platform) — conservative defaults.
    return BotContext(
        client=client,
        platform=client.platform,
        supports_web_app=False,
        supports_edit=False,
        supports_button_style=False,
        supports_copy_text=False,
    )
