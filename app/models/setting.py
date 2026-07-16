"""Key-value application settings editable from the admin panel."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


# Well-known setting keys (seeded on startup).
KEY_GYM_NAME = "gym_name"
KEY_CONTACT_TEXT = "contact_text"  # shown by "📞 راه‌های ارتباطی ما"
KEY_WELCOME_TEXT = "welcome_text"  # bot /start greeting
