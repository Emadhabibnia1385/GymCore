"""Phone normalization and Jalali date conversion."""

from datetime import date

from app.core.jalali import format_jalali, gregorian_to_jalali, parse_jalali
from app.core.phone import is_valid_phone, normalize_phone


def test_phone_normalization():
    assert normalize_phone("۰۹۱۲۳۴۵۶۷۸۹") == "09123456789"
    assert normalize_phone("+98 912 345 6789") == "09123456789"
    assert normalize_phone("9123456789") == "09123456789"
    assert is_valid_phone("09123456789")
    assert not is_valid_phone("0912")
    assert not is_valid_phone("08123456789")


def test_jalali_known_value():
    # 2026-07-19 Gregorian == 1405-04-28 Jalali.
    assert gregorian_to_jalali(2026, 7, 19) == (1405, 4, 28)
    assert format_jalali(date(2026, 7, 19)) == "1405/04/28"
    assert format_jalali(None) == "-"


def test_jalali_roundtrip():
    for d in [date(2026, 7, 19), date(2025, 3, 21), date(2024, 2, 29), date(2026, 1, 1)]:
        assert parse_jalali(format_jalali(d)) == d


def test_jalali_parse_edge_cases():
    assert parse_jalali("۱۴۰۵/۰۴/۲۸") == date(2026, 7, 19)
    assert parse_jalali("1405-04-28") == date(2026, 7, 19)
    assert parse_jalali("garbage") is None
    assert parse_jalali("1405/13/01") is None
