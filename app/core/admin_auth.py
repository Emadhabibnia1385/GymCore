"""Admin authorization — the numeric owner-ID whitelist.

Admin access is granted ONLY by matching the caller's numeric platform user ID
against the configured owner IDs (`TELEGRAM_OWNER_IDS` / `BALE_OWNER_IDS`).
Usernames are never trusted. The service layer (services.auth) additionally
honours a database COACH/ADMIN role, but this env whitelist is the root of
trust and cannot be bypassed by callback manipulation.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.models.enums import Platform


def owner_ids(platform: Platform) -> tuple[int, ...]:
    settings = get_settings()
    if platform == Platform.TELEGRAM:
        return settings.telegram_owner_id_list
    if platform == Platform.BALE:
        return settings.bale_owner_id_list
    return ()


def is_owner(platform: Platform, user_id: object) -> bool:
    """True iff `user_id` (int or numeric str) is a configured owner for `platform`."""
    try:
        uid = int(str(user_id).strip())
    except (TypeError, ValueError):
        return False
    return uid in owner_ids(platform)
