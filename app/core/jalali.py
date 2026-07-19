"""Gregorian ⇄ Jalali (شمسی) conversion for display and input parsing.

Standard arithmetic algorithm — no external dependency. All dates are stored
Gregorian in the database; Jalali is only for the Persian UI.
"""

from __future__ import annotations

from datetime import date, datetime

_G_DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
_J_DAYS_IN_MONTH = (31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29)

_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    g_day_no = 365 * (gy - 1600) + (gy - 1597) // 4 - (gy - 1501) // 100 + (gy - 1201) // 400
    for i in range(gm - 1):
        g_day_no += _G_DAYS_IN_MONTH[i]
    if gm > 2 and ((gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0):
        g_day_no += 1  # leap year, after February
    g_day_no += gd - 1

    j_day_no = g_day_no - 79
    j_np = j_day_no // 12053  # 12053 days = 33-year cycle
    j_day_no %= 12053
    jy = 979 + 33 * j_np + 4 * (j_day_no // 1461)
    j_day_no %= 1461
    if j_day_no >= 366:
        jy += (j_day_no - 1) // 365
        j_day_no = (j_day_no - 1) % 365
    if j_day_no < 186:
        jm = 1 + j_day_no // 31
        jd = 1 + j_day_no % 31
    else:
        jm = 7 + (j_day_no - 186) // 30
        jd = 1 + (j_day_no - 186) % 30
    return jy, jm, jd


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> date:
    """Inverse of :func:`gregorian_to_jalali`."""
    jy -= 979
    j_day_no = 365 * jy + (jy // 33) * 8 + (jy % 33 + 3) // 4
    for i in range(jm - 1):
        j_day_no += _J_DAYS_IN_MONTH[i]
    j_day_no += jd - 1

    g_day_no = j_day_no + 79
    gy = 1600 + 400 * (g_day_no // 146097)
    g_day_no %= 146097
    leap = True
    if g_day_no >= 36525:
        g_day_no -= 1
        gy += 100 * (g_day_no // 36524)
        g_day_no %= 36524
        if g_day_no >= 365:
            g_day_no += 1
        else:
            leap = False
    gy += 4 * (g_day_no // 1461)
    g_day_no %= 1461
    if g_day_no >= 366:
        leap = False
        g_day_no -= 1
        gy += g_day_no // 365
        g_day_no %= 365
    gd = g_day_no + 1
    months = list(_G_DAYS_IN_MONTH)
    if leap:
        months[1] = 29
    gm = 0
    for gm, days in enumerate(months, start=1):  # noqa: B007
        if gd <= days:
            break
        gd -= days
    return date(gy, gm, gd)


def format_jalali(value: date | datetime | None) -> str:
    """Format a date as `1404/04/28` for the Persian UI."""
    if value is None:
        return "-"
    if isinstance(value, datetime):
        value = value.date()
    jy, jm, jd = gregorian_to_jalali(value.year, value.month, value.day)
    return f"{jy}/{jm:02d}/{jd:02d}"


def parse_jalali(raw: str) -> date | None:
    """Parse `1404/04/28` (accepts Persian digits and `-`/`.` separators).

    Returns None when the text is not a valid Jalali date, so callers can ask
    the admin to re-enter it.
    """
    text = raw.strip().translate(_PERSIAN_DIGITS)
    for sep in ("/", "-", "."):
        text = text.replace(sep, "/")
    parts = [p for p in text.split("/") if p]
    if len(parts) != 3:
        return None
    try:
        jy, jm, jd = (int(p) for p in parts)
    except ValueError:
        return None
    if not (1 <= jm <= 12 and 1 <= jd <= 31 and 1000 <= jy <= 9999):
        return None
    try:
        gregorian = jalali_to_gregorian(jy, jm, jd)
    except (ValueError, OverflowError):
        return None
    # Round-trip guard: rejects impossible dates like 1404/12/31.
    if gregorian_to_jalali(gregorian.year, gregorian.month, gregorian.day) != (jy, jm, jd):
        return None
    return gregorian
