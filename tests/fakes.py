"""Offline fakes + helpers for bot handler tests (no real Telegram/Bale calls)."""

from __future__ import annotations

from app.bots.common.context import make_context
from app.bots.common.router import Dispatcher
from app.models import Platform


class FakeBotClient:
    """Records every outbound call instead of hitting a Bot API."""

    def __init__(self, platform: Platform = Platform.TELEGRAM):
        self.platform = platform
        self.sent: list[dict] = []
        self.answered: list[dict] = []
        self._mid = 100

    def _next_mid(self) -> int:
        self._mid += 1
        return self._mid

    def send_message(self, chat_id, text, reply_markup=None, disable_web_page_preview=True):
        mid = self._next_mid()
        self.sent.append(
            {"method": "send_message", "chat_id": chat_id, "text": text,
             "reply_markup": reply_markup, "message_id": mid}
        )
        return {"message_id": mid}

    def edit_message_text(self, chat_id, message_id, text, reply_markup=None,
                          disable_web_page_preview=True):
        self.sent.append(
            {"method": "edit_message_text", "chat_id": chat_id, "message_id": message_id,
             "text": text, "reply_markup": reply_markup}
        )
        return {"message_id": message_id}

    def edit_message_reply_markup(self, chat_id, message_id, reply_markup=None):
        self.sent.append(
            {"method": "edit_reply_markup", "chat_id": chat_id, "message_id": message_id,
             "reply_markup": reply_markup}
        )

    def answer_callback_query(self, callback_query_id, text=None, show_alert=False):
        self.answered.append({"id": callback_query_id, "text": text, "show_alert": show_alert})

    def delete_message(self, chat_id, message_id):
        self.sent.append({"method": "delete_message", "chat_id": chat_id, "message_id": message_id})

    def send_document_id(self, chat_id, file_id, caption=""):
        self.sent.append(
            {"method": "send_document_id", "chat_id": chat_id, "file_id": file_id,
             "caption": caption}
        )
        return {"message_id": self._next_mid()}

    def send_document_path(self, chat_id, file_path, filename, caption="", reply_markup=None):
        self.sent.append(
            {"method": "send_document_path", "chat_id": chat_id, "filename": filename,
             "caption": caption}
        )
        return {"message_id": self._next_mid()}

    def send_photo_id(self, chat_id, file_id, caption="", reply_markup=None):
        self.sent.append(
            {"method": "send_photo_id", "chat_id": chat_id, "file_id": file_id,
             "caption": caption, "reply_markup": reply_markup, "message_id": self._next_mid()}
        )
        return {"message_id": self._mid}

    def call(self, method, payload=None):
        return {"username": "testbot"}

    def close(self):
        pass


def make_dispatcher(platform: Platform = Platform.TELEGRAM):
    client = FakeBotClient(platform)
    return Dispatcher(make_context(client)), client


# --- update builders ---


def message_update(update_id, chat_id, user_id, text, first_name="کاربر", username=None):
    return {
        "update_id": update_id,
        "message": {
            "message_id": 10,
            "chat": {"id": chat_id},
            "from": {"id": user_id, "first_name": first_name, "username": username},
            "text": text,
        },
    }


def photo_message_update(update_id, chat_id, user_id, file_id="PHOTOID"):
    return {
        "update_id": update_id,
        "message": {
            "message_id": 10,
            "chat": {"id": chat_id},
            "from": {"id": user_id, "first_name": "کاربر"},
            "photo": [{"file_id": f"{file_id}_s"}, {"file_id": file_id}],
        },
    }


def contact_update(update_id, chat_id, user_id, phone=None):
    phone = phone or f"09{int(user_id):09d}"  # unique valid phone per user
    return {
        "update_id": update_id,
        "message": {
            "message_id": 10,
            "chat": {"id": chat_id},
            "from": {"id": user_id, "first_name": "کاربر"},
            "contact": {"phone_number": phone},
        },
    }


def register(disp, chat_id, user_id, phone=None):
    """Register a non-owner test user by sharing a unique phone (phone gate)."""
    disp.handle_update(contact_update(9000 + int(user_id) % 1000, chat_id, user_id, phone))


def callback_update(update_id, chat_id, user_id, data, message_id=10):
    return {
        "update_id": update_id,
        "callback_query": {
            "id": f"cbq-{update_id}",
            "data": data,
            "message": {"message_id": message_id, "chat": {"id": chat_id}},
            "from": {"id": user_id, "first_name": "کاربر"},
        },
    }


# --- markup inspection helpers ---


def button_texts(markup: dict) -> list[str]:
    return [b["text"] for row in markup["inline_keyboard"] for b in row]


def button_urls(markup: dict) -> list[str]:
    return [b["url"] for row in markup["inline_keyboard"] for b in row if "url" in b]


def web_app_urls(markup: dict) -> list[str]:
    return [b["web_app"]["url"] for row in markup["inline_keyboard"] for b in row if "web_app" in b]


def last_text(client: FakeBotClient) -> str:
    return client.sent[-1].get("text", "")


def last_markup(client: FakeBotClient) -> dict:
    return client.sent[-1]["reply_markup"]
