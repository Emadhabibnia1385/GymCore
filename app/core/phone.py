"""Phone number normalization.

Users type numbers with Persian/Arabic digits, spaces, or +98 prefixes.
We store one canonical form (`09xxxxxxxxx`) so lookups always match.
"""

_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_phone(raw: str) -> str:
    """Normalize to canonical local form. Returns '' for empty input."""
    phone = raw.strip().translate(_PERSIAN_DIGITS)
    phone = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    if phone.startswith("+98"):
        phone = "0" + phone[3:]
    elif phone.startswith("98") and len(phone) == 12:
        phone = "0" + phone[2:]
    elif phone and not phone.startswith("0") and len(phone) == 10:
        phone = "0" + phone
    return phone


def is_valid_phone(phone: str) -> bool:
    return len(phone) == 11 and phone.startswith("09") and phone.isdigit()
