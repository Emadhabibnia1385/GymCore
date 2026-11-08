"""Phone number normalization.

Users type numbers with Persian/Arabic digits, spaces, `+`/`00` prefixes, and a
contact shared from Telegram often arrives without its `+`. We store one
canonical form per number so lookups always match:

- Iranian mobiles keep the local form `09xxxxxxxxx` (everything stored before
  foreign numbers were accepted uses it, and cross-platform linking matches on it);
- any other country is `+<country code><number>`, e.g. `+447700900123`.
"""

_PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

# E.164 caps a full international number at 15 digits; 8 is the shortest real one.
_INTL_MIN, _INTL_MAX = 8, 15


def normalize_phone(raw: str) -> str:
    """Normalize to the canonical form. Returns '' for empty input."""
    phone = raw.strip().translate(_PERSIAN_DIGITS)
    phone = "".join(ch for ch in phone if ch.isdigit() or ch == "+")
    if phone.startswith("00"):
        phone = "+" + phone[2:]
    if phone.startswith("+98"):
        return "0" + phone[3:]
    if phone.startswith("98") and len(phone) == 12:
        return "0" + phone[2:]
    if phone and not phone.startswith(("0", "+")):
        if len(phone) == 10:
            return "0" + phone  # 9xxxxxxxxx — an Iranian mobile without its leading 0
        if len(phone) > 10:
            return "+" + phone  # a full international number without its +
    return phone


def is_valid_phone(phone: str) -> bool:
    """An Iranian mobile (`09xxxxxxxxx`) or an international number (`+…`)."""
    if phone.startswith("+"):
        digits = phone[1:]
        return digits.isdigit() and _INTL_MIN <= len(digits) <= _INTL_MAX
    return len(phone) == 11 and phone.startswith("09") and phone.isdigit()
