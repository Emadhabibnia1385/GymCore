"""Immediate push to clients / the coach via Telegram + Bale.

This is the low-level "send now" path used by domain events (attendance,
payment, new plan). Sends run in a daemon thread so an unreachable Bot API
never blocks or fails the originating request; failures are logged, never
raised. The scheduled/queued/idempotent notification system (with retries)
lives in `app/notifications/` and records rows in the `notifications` table.
"""

from __future__ import annotations

import logging
import threading

from sqlalchemy.orm import Session

from app.bots.common.client import build_client
from app.core.config import get_settings
from app.models import Person, Platform

logger = logging.getLogger(__name__)

# Tests and scripts flip this off to keep runs fully offline.
enabled = True

_BOT_PLATFORMS = (Platform.TELEGRAM, Platform.BALE)


def _send(platform: Platform, chat_id: str, text: str) -> bool:
    client = build_client(platform)
    if client is None:
        return False
    try:
        client.send_message(chat_id, text)
        return True
    except Exception:
        logger.warning("Failed to notify %s chat %s", platform.value, chat_id)
        return False
    finally:
        client.close()


def _dispatch(targets: list[tuple[Platform, str]], text: str) -> None:
    if not enabled or not targets:
        return

    def worker() -> None:
        for platform, chat_id in targets:
            _send(platform, chat_id, text)

    threading.Thread(target=worker, daemon=True).start()


def person_targets(person: Person) -> list[tuple[Platform, str]]:
    return [
        (identity.platform, identity.platform_user_id)
        for identity in person.identities
        if identity.platform in _BOT_PLATFORMS
    ]


def notify_person(db: Session, person: Person, text: str) -> None:
    """Send `text` to every bot account linked to this person."""
    _dispatch(person_targets(person), text)


def notify_owner(text: str) -> None:
    """Send `text` to every configured owner ID on every platform."""
    settings = get_settings()
    targets: list[tuple[Platform, str]] = []
    for owner_id in settings.telegram_owner_id_list:
        targets.append((Platform.TELEGRAM, str(owner_id)))
    for owner_id in settings.bale_owner_id_list:
        targets.append((Platform.BALE, str(owner_id)))
    _dispatch(targets, text)
