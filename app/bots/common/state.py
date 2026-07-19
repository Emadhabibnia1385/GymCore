"""Per-chat conversation state (in-memory, per bot process).

Used by multi-step admin flows (search, entering amounts/dates, uploading
files). The client flow is stateless (pure inline navigation). Keyed by
platform + chat so the same numeric chat id on Telegram and Bale never collide.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models import Platform


@dataclass
class ChatState:
    flow: str | None = None
    step: str | None = None
    data: dict = field(default_factory=dict)


class StateStore:
    def __init__(self) -> None:
        self._states: dict[str, ChatState] = {}

    @staticmethod
    def _key(platform: Platform, chat_id: object) -> str:
        return f"{platform.value}:{chat_id}"

    def get(self, platform: Platform, chat_id: object) -> ChatState | None:
        return self._states.get(self._key(platform, chat_id))

    def set(self, platform: Platform, chat_id: object, state: ChatState) -> None:
        self._states[self._key(platform, chat_id)] = state

    def clear(self, platform: Platform, chat_id: object) -> None:
        self._states.pop(self._key(platform, chat_id), None)
