"""The coach's clock: "now" and "today" in his timezone, not the server's.

The production server keeps UTC while the coach is in Tehran (UTC+3:30), so a
bare `date.today()` is still yesterday for him from midnight to 03:30 — the
attendance day view, «📅 امروز», the future-session check and the month a
report opens on would all be a day behind. Anything that asks "what day is it"
goes through here, in the configured `TIMEZONE` (Asia/Tehran).
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.config import get_settings

# Iran has kept standard time all year since 2022 — the fallback when the
# server has no tz database.
_TEHRAN = timezone(timedelta(hours=3, minutes=30), "Asia/Tehran")


@lru_cache
def _zone(name: str):
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return _TEHRAN


def local_now(now: datetime | None = None) -> datetime:
    """`now` in the coach's timezone. A naive datetime is UTC, as stored by the
    database (CURRENT_TIMESTAMP) and the notification ledger."""
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(_zone(get_settings().timezone))


def today(now: datetime | None = None) -> date:
    """The coach's calendar day."""
    return local_now(now).date()


def local_date(moment: datetime) -> date:
    """The coach's calendar day of a stored timestamp."""
    return local_now(moment).date()
