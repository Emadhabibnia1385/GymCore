"""Minimal Bot API client shared by Telegram and Bale.

Bale exposes a Telegram-compatible Bot API (https://tapi.bale.ai), so one HTTP
client serves both platforms — only the base URL and token differ. Kept
dependency-free (plain httpx) so we control exactly which API features are used
and both platforms stay compatible.

Security: the bot token lives only in the request URL; raised errors and logs
never include it (RuntimeError messages are hand-built, and the exception chain
is suppressed so httpx's tokened URL cannot leak into a traceback).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings
from app.models import Platform

logger = logging.getLogger(__name__)


class BotApiError(RuntimeError):
    """A Bot API call returned ok=false or the HTTP request failed."""


class BotClient:
    def __init__(self, base_url: str, token: str, platform: Platform):
        self.platform = platform
        self._base = base_url.rstrip("/")
        self._token = token
        self._api = f"{self._base}/bot{token}"
        self._http = httpx.Client(timeout=httpx.Timeout(35.0, connect=10.0))

    # --- low-level ---

    def _request(
        self,
        method: str,
        payload: dict[str, Any] | None = None,
        files: dict | None = None,
        data: dict | None = None,
    ) -> Any:
        try:
            if files is not None:
                response = self._http.post(
                    f"{self._api}/{method}", data=data or {}, files=files
                )
            else:
                response = self._http.post(f"{self._api}/{method}", json=payload or {})
            body = response.json()
        except httpx.HTTPError:
            # Do NOT chain (from) — httpx errors embed the tokened URL.
            raise BotApiError(f"{self.platform.value} API {method}: request failed") from None
        except ValueError:
            raise BotApiError(f"{self.platform.value} API {method}: invalid response") from None
        if not body.get("ok"):
            raise BotApiError(
                f"{self.platform.value} API {method} failed: {body.get('description')}"
            )
        return body.get("result")

    def call(self, method: str, payload: dict[str, Any] | None = None) -> Any:
        return self._request(method, payload)

    # --- polling ---

    def get_updates(self, offset: int | None = None, timeout: int = 30) -> list[dict]:
        payload: dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            payload["offset"] = offset
        return self._request("getUpdates", payload) or []

    # --- messaging ---

    def send_message(
        self,
        chat_id: int | str,
        text: str,
        reply_markup: dict | None = None,
        disable_web_page_preview: bool = True,
    ) -> dict:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return self._request("sendMessage", payload)

    def edit_message_text(
        self,
        chat_id: int | str,
        message_id: int,
        text: str,
        reply_markup: dict | None = None,
        disable_web_page_preview: bool = True,
    ) -> Any:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "disable_web_page_preview": disable_web_page_preview,
        }
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return self._request("editMessageText", payload)

    def edit_message_reply_markup(
        self, chat_id: int | str, message_id: int, reply_markup: dict | None = None
    ) -> Any:
        payload: dict[str, Any] = {"chat_id": chat_id, "message_id": message_id}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return self._request("editMessageReplyMarkup", payload)

    def answer_callback_query(
        self, callback_query_id: str, text: str | None = None, show_alert: bool = False
    ) -> Any:
        payload: dict[str, Any] = {"callback_query_id": callback_query_id}
        if text is not None:
            payload["text"] = text
        if show_alert:
            payload["show_alert"] = True
        return self._request("answerCallbackQuery", payload)

    def delete_message(self, chat_id: int | str, message_id: int) -> Any:
        return self._request("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

    # --- files ---

    def send_document_path(
        self,
        chat_id: int | str,
        file_path: Path,
        filename: str,
        caption: str = "",
        reply_markup: dict | None = None,
    ) -> dict:
        """Upload a local file as a document (multipart)."""
        data: dict[str, Any] = {"chat_id": str(chat_id), "caption": caption}
        if reply_markup is not None:
            import json

            data["reply_markup"] = json.dumps(reply_markup)
        with open(file_path, "rb") as fh:
            return self._request(
                "sendDocument", files={"document": (filename, fh)}, data=data
            )

    def send_document_id(
        self, chat_id: int | str, file_id: str, caption: str = ""
    ) -> dict:
        """Re-send a document already hosted on the platform by its file_id."""
        return self._request(
            "sendDocument", {"chat_id": chat_id, "document": file_id, "caption": caption}
        )

    def send_photo_id(
        self, chat_id: int | str, file_id: str, caption: str = "", reply_markup: dict | None = None
    ) -> dict:
        payload: dict[str, Any] = {"chat_id": chat_id, "photo": file_id, "caption": caption}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return self._request("sendPhoto", payload)

    def set_my_commands(self, commands: list[dict]) -> Any:
        """Register the bot's command list (e.g. /start) shown in the UI menu."""
        return self._request("setMyCommands", {"commands": commands})

    def get_file(self, file_id: str) -> dict:
        return self._request("getFile", {"file_id": file_id})

    def download_file(self, file_path: str) -> bytes:
        """Download a file the platform exposed via getFile().file_path."""
        try:
            response = self._http.get(f"{self._base}/file/bot{self._token}/{file_path}")
            response.raise_for_status()
        except httpx.HTTPError:
            raise BotApiError(f"{self.platform.value} download failed") from None
        return response.content

    def close(self) -> None:
        self._http.close()


def build_client(platform: Platform) -> BotClient | None:
    """Build a client for a platform, or None when its token isn't configured."""
    settings = get_settings()
    if platform == Platform.TELEGRAM and settings.telegram_bot_token:
        return BotClient(
            settings.telegram_api_base, settings.telegram_bot_token, Platform.TELEGRAM
        )
    if platform == Platform.BALE and settings.bale_bot_token:
        return BotClient(settings.bale_api_base, settings.bale_bot_token, Platform.BALE)
    return None
