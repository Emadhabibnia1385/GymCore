"""Key-value application settings, editable from the in-bot admin panel.

The seeded defaults below are the *initial* content; once a coach edits a value
in the admin panel it is persisted and overrides the default. Message copy that
the coach may want to reword lives here (not scattered in handlers).
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Platform, Setting
from app.models.setting import (
    KEY_BALE_OWNER_CONTACT,
    KEY_CARD_NUMBER,
    KEY_COACH_NAME,
    KEY_CONTACT_INTRO,
    KEY_DEFAULT_ALLOWED_ABSENCE,
    KEY_GYM_NAME,
    KEY_LOW_SESSION_THRESHOLD,
    KEY_MAIN_INTRO,
    KEY_NOTIFY_ON_ATTENDANCE,
    KEY_PLAN_ORDER_TEXT,
    KEY_REGISTER_CONTACT_TEXT,
    KEY_SIGNUP_URL,
    KEY_TELEGRAM_OWNER_CONTACT,
)


def _defaults() -> dict[str, str]:
    cfg = get_settings()
    return {
        KEY_GYM_NAME: "GymCore",
        KEY_COACH_NAME: "مهدی سرمد",
        KEY_CARD_NUMBER: "",
        KEY_MAIN_INTRO: (
            "به GymCore خوش آمدی 🟢🏋️\n"
            "همراهِ تو در مسیر تمرین و تناسب‌اندام. از منوی زیر شروع کن."
        ),
        # «ثبت‌نام در کلاس‌ها» — exactly per product spec.
        KEY_REGISTER_CONTACT_TEXT: (
            "برای ثبت‌نام در کلاس‌ها و هماهنگی درباره نوع کلاس، زمان‌بندی، تعداد جلسات و "
            "هزینه، از طریق یکی از راه‌های ارتباطی زیر با من در تماس باشید تا بهترین گزینه "
            "را با هم هماهنگ کنیم. 👇"
        ),
        # «سفارش برنامه»
        KEY_PLAN_ORDER_TEXT: (
            "برای سفارش برنامه تمرینی یا تغذیه، از طریق دکمه زیر وارد فرم ثبت سفارش شوید."
        ),
        # «راه‌های ارتباطی ما»
        KEY_CONTACT_INTRO: "از هر راهی که برایت راحت‌تر است، در دسترستم 🟢",
        KEY_SIGNUP_URL: cfg.signup_url,
        KEY_DEFAULT_ALLOWED_ABSENCE: "1",
        KEY_LOW_SESSION_THRESHOLD: str(cfg.low_session_threshold),
        KEY_TELEGRAM_OWNER_CONTACT: "https://t.me/mahdisarmadcoach",
        KEY_BALE_OWNER_CONTACT: "",
        KEY_NOTIFY_ON_ATTENDANCE: "1",
    }


def start_poster_key(platform: Platform) -> str:
    """Per-platform setting key holding the start-menu poster's file_id."""
    return f"start_poster_{platform.value.lower()}"


def get_value(db: Session, key: str, default: str = "") -> str:
    setting = db.get(Setting, key)
    if setting is not None:
        return setting.value
    return _defaults().get(key, default)


def get_int(db: Session, key: str, default: int = 0) -> int:
    try:
        return int(get_value(db, key, str(default)).strip())
    except (ValueError, AttributeError):
        return default


def get_bool(db: Session, key: str, default: bool = False) -> bool:
    value = get_value(db, key, "1" if default else "0").strip().lower()
    return value in {"1", "true", "yes", "on", "بله"}


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
    values = dict(_defaults())
    for setting in db.query(Setting).all():
        values[setting.key] = setting.value
    return values


def seed_defaults(db: Session) -> None:
    """Insert default settings that don't exist yet (idempotent, run at startup)."""
    changed = False
    for key, value in _defaults().items():
        if db.get(Setting, key) is None:
            db.add(Setting(key=key, value=value))
            changed = True
    if changed:
        db.commit()
