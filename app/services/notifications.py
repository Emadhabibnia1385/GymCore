"""Push notifications to clients and the gym owner via Telegram/Bale.

Sends run in a daemon thread so an unreachable Bot API never blocks or
fails the originating request. Failures are logged, never raised.
"""

from __future__ import annotations

import logging
import threading

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.bots.client import build_client
from app.models import ChannelIdentity, Person, Platform

logger = logging.getLogger(__name__)

# Tests and scripts can flip this off to keep runs offline.
enabled = True

_BOT_PLATFORMS = (Platform.TELEGRAM, Platform.BALE)


def _send(platform: Platform, chat_id: str, text: str) -> None:
    client = build_client(platform)
    if client is None:
        return
    try:
        client.send_message(chat_id, text)
    except Exception:
        logger.warning("Failed to notify %s chat %s", platform.value, chat_id)
    finally:
        client.close()


def _dispatch(targets: list[tuple[Platform, str]], text: str) -> None:
    if not enabled or not targets:
        return

    def worker() -> None:
        for platform, chat_id in targets:
            _send(platform, chat_id, text)

    threading.Thread(target=worker, daemon=True).start()


def notify_person(db: Session, person: Person, text: str) -> None:
    """Send `text` to every bot account linked to this person."""
    targets = [
        (identity.platform, identity.platform_user_id)
        for identity in person.identities
        if identity.platform in _BOT_PLATFORMS
    ]
    _dispatch(targets, text)


def notify_owner(text: str) -> None:
    """Send `text` to the gym owner on every configured platform."""
    settings = get_settings()
    targets: list[tuple[Platform, str]] = []
    if settings.telegram_owner_id:
        targets.append((Platform.TELEGRAM, settings.telegram_owner_id))
    if settings.bale_owner_id:
        targets.append((Platform.BALE, settings.bale_owner_id))
    _dispatch(targets, text)
