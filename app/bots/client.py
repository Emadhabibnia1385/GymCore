"""Minimal Bot API client shared by Telegram and Bale.

Bale exposes a Telegram-compatible Bot API (https://tapi.bale.ai), so one
HTTP client serves both platforms — only the base URL and token differ.
Kept dependency-free (plain httpx) so we control exactly which API
features are used and both platforms stay compatible.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

from app.core.config import get_settings
from app.models import Platform

logger = logging.getLogger(__name__)


class BotClient:
    def __init__(self, base_url: str, token: str, platform: Platform):
        self.platform = platform
        self._api = f"{base_url.rstrip('/')}/bot{token}"
        self._http = httpx.Client(timeout=httpx.Timeout(35.0, connect=10.0))

    def call(self, method: str, payload: dict[str, Any] | None = None) -> Any:
        """Call a Bot API method; returns the `result` field."""
        response = self._http.post(f"{self._api}/{method}", json=payload or {})
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(
                f"{self.platform.value} API {method} failed: {data.get('description')}"
            )
        return data.get("result")

    def get_updates(self, offset: int | None = None, timeout: int = 30) -> list[dict]:
        payload: dict[str, Any] = {"timeout": timeout}
        if offset is not None:
            payload["offset"] = offset
        return self.call("getUpdates", payload) or []

    def send_message(
        self, chat_id: int | str, text: str, reply_markup: dict | None = None
    ) -> dict:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return self.call("sendMessage", payload)

    def send_document(
        self, chat_id: int | str, file_path: Path, filename: str, caption: str = ""
    ) -> dict:
        """Upload a local file as a document (multipart, not JSON)."""
        with open(file_path, "rb") as fh:
            response = self._http.post(
                f"{self._api}/sendDocument",
                data={"chat_id": str(chat_id), "caption": caption},
                files={"document": (filename, fh)},
            )
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(
                f"{self.platform.value} sendDocument failed: {data.get('description')}"
            )
        return data.get("result")

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
