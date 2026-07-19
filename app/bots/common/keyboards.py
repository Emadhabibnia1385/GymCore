"""Inline ("glass") keyboard builders — Telegram Bot API format, Bale-compatible.

Every client-facing keyboard is inline. Telegram and Bale cannot colour buttons,
so green cues live in the labels (🟢/✅) and message content, never in unsupported
colour APIs.
"""

from __future__ import annotations

from app.bots.common import callbacks as cb
from app.copy import texts
from app.models import ContactLink


def _inline(rows: list[list[dict]]) -> dict:
    return {"inline_keyboard": rows}


# Telegram button styles (Bot API, Feb 2026): coloured button backgrounds.
STYLE_PRIMARY = "primary"  # blue
STYLE_SUCCESS = "success"  # green
STYLE_DANGER = "danger"  # red


def button(text: str, data: str, style: str | None = None) -> dict:
    btn = {"text": text, "callback_data": data}
    if style:
        btn["style"] = style
    return btn


def url_button(text: str, url: str, style: str | None = None) -> dict:
    btn = {"text": text, "url": url}
    if style:
        btn["style"] = style
    return btn


def copy_button(text: str, copy_value: str, style: str | None = None) -> dict:
    """A tap-to-copy button (Telegram `copy_text`) — used for phone/email."""
    btn = {"text": text, "copy_text": {"text": copy_value[:256]}}
    if style:
        btn["style"] = style
    return btn


# Telegram/Bale only accept these schemes for inline URL buttons; mailto:/tel:
# are rejected (Bad Request: BUTTON_URL_INVALID) and would fail the whole message.
_BUTTON_URL_SCHEMES = ("http://", "https://", "tg://")


def is_button_url(url: str) -> bool:
    return (url or "").lower().startswith(_BUTTON_URL_SCHEMES)


def _order_button(signup_url: str, style: str | None = None) -> dict:
    """«سفارش برنامه» opens the signup as a plain link (not a Mini App).

    Falls back to a callback only if no signup URL is configured.
    """
    if signup_url and is_button_url(signup_url):
        return url_button(texts.BTN_ORDER_PLAN, signup_url, style=style)
    return button(texts.BTN_ORDER_PLAN, cb.ORDER, style=style)


def main_menu(is_admin: bool = False, signup_url: str = "", styled: bool = False) -> dict:
    """Main client menu. When `styled` (Telegram), buttons carry colour styles:
    blue = register/order, green = my classes/programs, red = contact.
    """
    def st(value: str) -> str | None:
        return value if styled else None

    rows = [
        [button(texts.BTN_REGISTER_CLASS, cb.REGISTER, st(STYLE_PRIMARY)),
         _order_button(signup_url, st(STYLE_PRIMARY))],
        [button(texts.BTN_MY_CLASSES, cb.COURSES, st(STYLE_SUCCESS)),
         button(texts.BTN_MY_PLANS, cb.PROGRAMS, st(STYLE_SUCCESS))],
        [button(texts.BTN_CONTACT, cb.CONTACT, st(STYLE_DANGER))],
    ]
    if is_admin:
        rows.append([button(texts.BTN_ADMIN_PANEL, cb.ADMIN)])
    return _inline(rows)


def back_to_menu() -> dict:
    return _inline([[button(texts.BTN_BACK_TO_MENU, cb.HOME)]])


def contact_links(
    links: list[ContactLink], styled: bool = False, support_copy: bool = False
) -> dict:
    """Contact links keyboard. Web links → URL buttons; mailto:/tel: → tap-to-copy
    buttons when supported (Telegram), otherwise omitted (caller shows them as
    text). When `styled`, every button is green (success)."""
    style = STYLE_SUCCESS if styled else None
    rows: list[list[dict]] = []
    for link in links:
        label = f"{link.icon + ' ' if link.icon else ''}{link.label}"
        if is_button_url(link.url):
            rows.append([url_button(label, link.url, style=style)])
        elif support_copy:
            value = link.url.split(":", 1)[1] if ":" in link.url else link.url
            rows.append([copy_button(label, value, style=style)])
    rows.append([button(texts.BTN_BACK_TO_MENU, cb.HOME, style=style)])
    return _inline(rows)


def plan_signup(url: str) -> dict:
    """The plan-order signup button — a plain URL link (opens the website)."""
    return _inline(
        [[url_button(texts.BTN_PLAN_SIGNUP, url)], [button(texts.BTN_BACK_TO_MENU, cb.HOME)]]
    )


def course_list(items: list[tuple[int, str, int]]) -> dict:
    """items: (course_id, class_title, remaining_sessions)."""
    rows = [
        [button(f"🟢 {title} | {remaining} جلسه باقی‌مانده", cb.course(course_id))]
        for course_id, title, remaining in items
    ]
    rows.append([button(texts.BTN_BACK_TO_MENU, cb.HOME)])
    return _inline(rows)


def course_detail_nav() -> dict:
    return _inline(
        [[button(texts.BTN_BACK, cb.COURSES)], [button(texts.BTN_HOME, cb.HOME)]]
    )


def program_list(items: list[tuple[int, str]]) -> dict:
    """items: (assignment_id, label)."""
    rows = [[button(f"🟢 {label}", cb.program(assignment_id))] for assignment_id, label in items]
    rows.append([button(texts.BTN_BACK_TO_MENU, cb.HOME)])
    return _inline(rows)


def program_detail_nav() -> dict:
    return _inline(
        [[button(texts.BTN_BACK, cb.PROGRAMS)], [button(texts.BTN_HOME, cb.HOME)]]
    )


def admin_menu() -> dict:
    """The admin panel main menu (shown only to authorized owners)."""
    return _inline(
        [
            [button(texts.BTN_ADMIN_STUDENTS, cb.admin("students"))],
            [button(texts.BTN_ADMIN_CLASSES, cb.admin("classes")),
             button(texts.BTN_ADMIN_COURSES, cb.admin("courses"))],
            [button(texts.BTN_ADMIN_ATTENDANCE, cb.admin("attend"))],
            [button(texts.BTN_ADMIN_PLANS, cb.admin("plans")),
             button(texts.BTN_ADMIN_PAYMENTS, cb.admin("pay"))],
            [button(texts.BTN_ADMIN_NOTIFY, cb.admin("notify")),
             button(texts.BTN_ADMIN_SETTINGS, cb.admin("settings"))],
            [button(texts.BTN_ADMIN_EXIT, cb.HOME)],
        ]
    )
