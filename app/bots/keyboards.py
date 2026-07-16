"""Reply keyboards (Telegram Bot API format — Bale compatible)."""

from __future__ import annotations

from app.bots import texts


def _keyboard(rows: list[list[dict]]) -> dict:
    return {"keyboard": rows, "resize_keyboard": True}


def main_menu() -> dict:
    return _keyboard(
        [
            [{"text": texts.BTN_REGISTER_CLASS}],
            [{"text": texts.BTN_ORDER_PLAN}],
            [{"text": texts.BTN_MY_CLASSES}, {"text": texts.BTN_MY_PLANS}],
            [{"text": texts.BTN_CONTACT}],
        ]
    )


def share_phone() -> dict:
    return _keyboard([[{"text": texts.BTN_SHARE_PHONE, "request_contact": True}]])


def class_list(titles: list[str]) -> dict:
    rows = [[{"text": title}] for title in titles]
    rows.append([{"text": texts.BTN_BACK}])
    return _keyboard(rows)


def plan_types() -> dict:
    return _keyboard(
        [
            [{"text": texts.BTN_PLAN_TRAINING}],
            [{"text": texts.BTN_PLAN_NUTRITION}],
            [{"text": texts.BTN_PLAN_CUSTOM}],
            [{"text": texts.BTN_BACK}],
        ]
    )


def note_or_skip() -> dict:
    return _keyboard([[{"text": texts.BTN_NO_NOTE}], [{"text": texts.BTN_BACK}]])


def remove() -> dict:
    return {"remove_keyboard": True}
