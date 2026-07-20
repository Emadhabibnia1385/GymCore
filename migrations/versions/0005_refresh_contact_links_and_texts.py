"""refresh contact links (new order/labels + bale) and the registration message

Content refresh for existing deployments: resets contact_links to the coach's
requested set and updates the registration message. New/SQLite installs get the
same content from the app's startup seeding.

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-20 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0005'
down_revision: str | None = '0004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_LINKS = [
    {"key": "phone", "label": "تلفن: 09305560950", "icon": "📞", "url": "tel:09305560950",
     "active": True, "sort_order": 1, "platform": None},
    {"key": "telegram", "label": "تلگرام: @MahdiSarmad1", "icon": "✈️",
     "url": "https://t.me/MahdiSarmad1", "active": True, "sort_order": 2, "platform": "TELEGRAM"},
    {"key": "instagram", "label": "اینستاگرام: @mahdisarmad", "icon": "📸",
     "url": "https://instagram.com/mahdisarmad", "active": True, "sort_order": 3, "platform": None},
    {"key": "bale", "label": "بله: @mahdisarmad", "icon": "💬",
     "url": "https://ble.ir/mahdisarmad", "active": True, "sort_order": 4, "platform": "BALE"},
    {"key": "whatsapp", "label": "واتساپ: 09305560950", "icon": "🟢",
     "url": "https://wa.me/989305560950", "active": True, "sort_order": 5, "platform": None},
    {"key": "linkedin", "label": "لینکدین: mahdisarmad", "icon": "💼",
     "url": "https://linkedin.com/in/mahdisarmad", "active": True, "sort_order": 6, "platform": None},
    {"key": "email", "label": "ایمیل: mahdisarmad59@gmail.com", "icon": "📧",
     "url": "mailto:mahdisarmad59@gmail.com", "active": True, "sort_order": 7, "platform": None},
    {"key": "website", "label": "وب‌سایت: mahdisarmad.ir", "icon": "🌐",
     "url": "https://mahdisarmad.ir/", "active": True, "sort_order": 8, "platform": None},
]

_REGISTER_TEXT = (
    "🏋️‍♂️ ثبت‌نام در کلاس‌ها\n\n"
    "برای هماهنگی و ثبت‌نام، درباره‌ی این موارد با هم صحبت می‌کنیم:\n"
    "🔹 نوع کلاس\n"
    "🔹 زمان‌بندی جلسات\n"
    "🔹 تعداد جلسات\n"
    "🔹 هزینه\n\n"
    "از یکی از راه‌های ارتباطی زیر با من در تماس باش تا بهترین گزینه را با هم انتخاب کنیم. 👇"
)


def upgrade() -> None:
    contact = sa.table(
        "contact_links",
        sa.column("key", sa.String),
        sa.column("label", sa.String),
        sa.column("url", sa.String),
        sa.column("icon", sa.String),
        sa.column("active", sa.Boolean),
        sa.column("sort_order", sa.Integer),
        sa.column("platform", sa.String),
    )
    op.execute("DELETE FROM contact_links")
    op.bulk_insert(contact, _LINKS)

    # Upsert the registration message setting.
    op.execute("DELETE FROM settings WHERE key = 'registration_contact_message'")
    settings_tbl = sa.table("settings", sa.column("key", sa.String), sa.column("value", sa.Text))
    op.bulk_insert(settings_tbl, [{"key": "registration_contact_message", "value": _REGISTER_TEXT}])


def downgrade() -> None:
    # Content refresh — no meaningful reverse (app re-seeds defaults on startup).
    pass
