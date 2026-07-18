"""Reply/inline keyboards (Telegram Bot API format — Bale compatible)."""

from __future__ import annotations

from app.bots import texts
from app.models import Platform


def _keyboard(rows: list[list[dict]]) -> dict:
    return {"keyboard": rows, "resize_keyboard": True}


def main_menu() -> dict:
    # «ثبت‌نام کلاس» و «سفارش برنامه» کنار هم در یک ردیف.
    return _keyboard(
        [
            [{"text": texts.BTN_REGISTER_CLASS}, {"text": texts.BTN_ORDER_PLAN}],
            [{"text": texts.BTN_MY_CLASSES}, {"text": texts.BTN_MY_PLANS}],
            [{"text": texts.BTN_CONTACT}],
        ]
    )


def share_phone() -> dict:
    return _keyboard([[{"text": texts.BTN_SHARE_PHONE, "request_contact": True}]])


def plan_signup(platform: Platform, url: str) -> dict:
    """Inline button that opens the plan-order signup.

    Telegram opens it inside the app as a Mini App (``web_app``); Bale — which
    does not support Web Apps — falls back to a normal URL button.
    """
    if platform == Platform.TELEGRAM:
        button = {"text": texts.BTN_PLAN_SIGNUP, "web_app": {"url": url}}
    else:
        button = {"text": texts.BTN_PLAN_SIGNUP, "url": url}
    return {"inline_keyboard": [[button]]}


def remove() -> dict:
    return {"remove_keyboard": True}
