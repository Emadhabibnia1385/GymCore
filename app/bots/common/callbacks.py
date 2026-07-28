"""Inline callback-data scheme (namespaced, compact, validated).

Telegram limits callback_data to 64 bytes, so tokens are short. Data is
`action` optionally followed by `:rest`. Every inbound callback is parsed and
validated by the router; unknown/garbage data is ignored (tamper defence).

Admin callbacks all start with the ``a:`` prefix so the router can gate them
behind an authorization check before any admin handler runs.
"""

from __future__ import annotations

SEP = ":"
ADMIN_PREFIX = "a"

# --- Client menu actions (no argument) ---
HOME = "home"
REGISTER = "reg"
ORDER = "ord"
COURSES = "crs"
PROGRAMS = "prg"
CONTACT = "con"
ADMIN = "adm"
SCHEDULE = "sch"
NOOP = "noop"


def course(course_id: int) -> str:
    return f"{COURSES}{SEP}{course_id}"


def schedule(course_id: int, page: int = 1) -> str:
    """The client's read-only session grid, e.g. 'sch:12:2'."""
    return f"{SCHEDULE}{SEP}{course_id}{SEP}{page}"


def parse_pair(rest: str | None) -> tuple[int | None, int]:
    """Split `<id>[:<page>]` into a validated id and a page (default 1)."""
    first, _, second = (rest or "").partition(SEP)
    return parse_int(first or None), (parse_int(second or None) or 1)


def program(assignment_id: int) -> str:
    return f"{PROGRAMS}{SEP}{assignment_id}"


def admin(*parts: object) -> str:
    """Build an admin callback, e.g. admin('students', 'page', 2) -> 'a:students:page:2'."""
    return SEP.join([ADMIN_PREFIX, *(str(p) for p in parts)])


def parse(data: str) -> tuple[str, str | None]:
    """Split callback data into (action, rest); rest is None when absent."""
    action, _, rest = (data or "").partition(SEP)
    return action, (rest or None)


def parse_int(rest: str | None) -> int | None:
    """Parse a positive integer argument, or None if invalid (tamper-safe)."""
    if rest is None:
        return None
    try:
        value = int(rest)
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None
