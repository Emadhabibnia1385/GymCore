"""Key-value application settings editable from the in-bot admin panel.

Everything variable (messages, card number, thresholds, owner contacts) lives
here so normal content updates never require a code change.
"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


# --- Well-known setting keys (seeded on startup) ---
KEY_GYM_NAME = "gym_name"
KEY_COACH_NAME = "coach_display_name"
KEY_CARD_NUMBER = "card_number"
KEY_MAIN_INTRO = "main_intro_message"  # /start greeting
KEY_REGISTER_CONTACT_TEXT = "registration_contact_message"  # «ثبت‌نام در کلاس‌ها»
KEY_PLAN_ORDER_TEXT = "plan_order_message"  # «سفارش برنامه»
KEY_CONTACT_INTRO = "contact_intro_message"  # «راه‌های ارتباطی ما»
KEY_SIGNUP_URL = "signup_url"
KEY_DEFAULT_ALLOWED_ABSENCE = "default_allowed_absence"
KEY_LOW_SESSION_THRESHOLD = "low_session_threshold"
KEY_TELEGRAM_OWNER_CONTACT = "telegram_owner_contact"
KEY_BALE_OWNER_CONTACT = "bale_owner_contact"
KEY_NOTIFY_ON_ATTENDANCE = "notify_on_attendance"
KEY_BUTTON_STYLE = "button_style_enabled"  # colour the Telegram menu buttons
