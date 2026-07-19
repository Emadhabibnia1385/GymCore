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


def _order_button(signup_url: str, supports_web_app: bool) -> dict:
    """«سفارش برنامه» opens the signup directly — Mini App on Telegram, URL on Bale.

    Falls back to a callback only if no signup URL is configured.
    """
    if signup_url:
        if supports_web_app:
            return {"text": texts.BTN_ORDER_PLAN, "web_app": {"url": signup_url}}
        return url_button(texts.BTN_ORDER_PLAN, signup_url)
    return button(texts.BTN_ORDER_PLAN, cb.ORDER)


def main_menu(is_admin: bool = False, signup_url: str = "", supports_web_app: bool = False) -> dict:
    rows = [
        [button(texts.BTN_REGISTER_CLASS, cb.REGISTER),
         _order_button(signup_url, supports_web_app)],
        [button(texts.BTN_MY_CLASSES, cb.COURSES), button(texts.BTN_MY_PLANS, cb.PROGRAMS)],
        [button(texts.BTN_CONTACT, cb.CONTACT)],
    ]
    if is_admin:
        rows.append([button(texts.BTN_ADMIN_PANEL, cb.ADMIN)])
    return _inline(rows)


def back_to_menu() -> dict:
    return _inline([[button(texts.BTN_BACK_TO_MENU, cb.HOME)]])


def contact_links(links: list[ContactLink]) -> dict:
    """URL buttons for each active contact link + a back-to-menu row."""
    rows = [
        [url_button(f"{link.icon + ' ' if link.icon else ''}{link.label}", link.url)]
        for link in links
    ]
    rows.append([button(texts.BTN_BACK_TO_MENU, cb.HOME)])
    return _inline(rows)


def plan_signup(url: str, supports_web_app: bool) -> dict:
    """The plan-order signup button (Mini App on Telegram, URL button on Bale)."""
    if supports_web_app:
        signup = {"text": texts.BTN_PLAN_SIGNUP, "web_app": {"url": url}}
    else:
        signup = url_button(texts.BTN_PLAN_SIGNUP, url)
    return _inline([[signup], [button(texts.BTN_BACK_TO_MENU, cb.HOME)]])


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
