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


def button(text: str, data: str) -> dict:
    return {"text": text, "callback_data": data}


def url_button(text: str, url: str) -> dict:
    return {"text": text, "url": url}


# Telegram/Bale only accept these schemes for inline URL buttons; mailto:/tel:
# are rejected (Bad Request: BUTTON_URL_INVALID) and would fail the whole message.
_BUTTON_URL_SCHEMES = ("http://", "https://", "tg://")


def is_button_url(url: str) -> bool:
    return (url or "").lower().startswith(_BUTTON_URL_SCHEMES)


def _order_button(signup_url: str) -> dict:
    """«سفارش برنامه» opens the signup as a plain link (not a Mini App).

    Falls back to a callback only if no signup URL is configured.
    """
    if signup_url and is_button_url(signup_url):
        return url_button(texts.BTN_ORDER_PLAN, signup_url)
    return button(texts.BTN_ORDER_PLAN, cb.ORDER)


def main_menu(is_admin: bool = False, signup_url: str = "") -> dict:
    rows = [
        [button(texts.BTN_REGISTER_CLASS, cb.REGISTER), _order_button(signup_url)],
        [button(texts.BTN_MY_CLASSES, cb.COURSES), button(texts.BTN_MY_PLANS, cb.PROGRAMS)],
        [button(texts.BTN_CONTACT, cb.CONTACT)],
    ]
    if is_admin:
        rows.append([button(texts.BTN_ADMIN_PANEL, cb.ADMIN)])
    return _inline(rows)


def back_to_menu() -> dict:
    return _inline([[button(texts.BTN_BACK_TO_MENU, cb.HOME)]])


def contact_links(links: list[ContactLink]) -> dict:
    """URL buttons for each active contact link + a back-to-menu row.

    Only links with a button-safe scheme become buttons; mailto:/tel: links are
    shown as text by the caller (they cannot be inline buttons).
    """
    rows = [
        [url_button(f"{link.icon + ' ' if link.icon else ''}{link.label}", link.url)]
        for link in links
        if is_button_url(link.url)
    ]
    rows.append([button(texts.BTN_BACK_TO_MENU, cb.HOME)])
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
