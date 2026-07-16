"""Gregorian → Jalali (شمسی) conversion for display formatting.

Standard arithmetic algorithm — no external dependency. Only used for
rendering; all dates are stored as Gregorian in the database.
"""

from __future__ import annotations

from datetime import date, datetime

_G_DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


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


def format_jalali(value: date | datetime | None) -> str:
    """Format a date as `1404/04/25` for the Persian UI."""
    if value is None:
        return "-"
    if isinstance(value, datetime):
        value = value.date()
    jy, jm, jd = gregorian_to_jalali(value.year, value.month, value.day)
    return f"{jy}/{jm:02d}/{jd:02d}"
