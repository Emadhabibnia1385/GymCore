"""Pure utility tests: phone normalization, Jalali conversion, passwords."""

from datetime import date

from app.core.jalali import format_jalali, gregorian_to_jalali
from app.core.phone import is_valid_phone, normalize_phone
from app.core.security import hash_password, verify_password


def test_normalize_phone_variants():
    assert normalize_phone("09123456789") == "09123456789"
    assert normalize_phone("+989123456789") == "09123456789"
    assert normalize_phone("989123456789") == "09123456789"
    assert normalize_phone("9123456789") == "09123456789"
    assert normalize_phone("۰۹۱۲۳۴۵۶۷۸۹") == "09123456789"
    assert normalize_phone("0912 345 6789") == "09123456789"


def test_is_valid_phone():
    assert is_valid_phone("09123456789")
    assert not is_valid_phone("0912345678")  # too short
    assert not is_valid_phone("08123456789")  # wrong prefix


def test_jalali_known_dates():
    assert gregorian_to_jalali(2026, 3, 21) == (1405, 1, 1)  # Nowruz 1405
    assert gregorian_to_jalali(2026, 7, 16) == (1405, 4, 25)
    assert format_jalali(date(2026, 3, 21)) == "1405/01/01"


def test_password_hash_roundtrip():
    stored = hash_password("s3cret-pass")
    assert verify_password("s3cret-pass", stored)
    assert not verify_password("wrong", stored)
    assert not verify_password("s3cret-pass", "garbage")
