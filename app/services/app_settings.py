"""Key-value application settings (gym name, contact text, welcome text)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Setting
from app.models.setting import KEY_CONTACT_TEXT, KEY_GYM_NAME, KEY_WELCOME_TEXT

_DEFAULTS = {
    KEY_GYM_NAME: "GymCore",
    KEY_CONTACT_TEXT: "برای ارتباط با مربی از همین ربات پیام بدهید.",
    KEY_WELCOME_TEXT: "به باشگاه خوش آمدید! 🏋️",
}


def get_value(db: Session, key: str) -> str:
    setting = db.get(Setting, key)
    if setting is not None:
        return setting.value
    return _DEFAULTS.get(key, "")


def set_value(db: Session, key: str, value: str) -> Setting:
    setting = db.get(Setting, key)
    if setting is None:
        setting = Setting(key=key, value=value)
        db.add(setting)
    else:
        setting.value = value
    db.commit()
    return setting


def get_all(db: Session) -> dict[str, str]:
    values = dict(_DEFAULTS)
    for setting in db.query(Setting).all():
        values[setting.key] = setting.value
    return values


def seed_defaults(db: Session) -> None:
    """Insert default settings that don't exist yet (startup)."""
    for key, value in _DEFAULTS.items():
        if db.get(Setting, key) is None:
            db.add(Setting(key=key, value=value))
    db.commit()
