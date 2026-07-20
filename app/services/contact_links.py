"""Coach contact links — admin-managed, never hardcoded in handlers.

The client «راه‌های ارتباطی ما» screen and the class-registration screen render
whatever active links exist here, in `sort_order`. An optional `platform` hint
features a link on its own platform (e.g. the Telegram link on Telegram).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models import ContactLink, Platform

# Order + labels-with-values per the coach's request. Phone/email are tap-to-copy
# on Telegram; the rest are link buttons. Colours alternate blue/green in the UI.
_DEFAULT_LINKS = [
    {"key": "phone", "label": "تلفن: 09305560950", "icon": "📞",
     "url": "tel:09305560950", "sort_order": 1},
    {"key": "telegram", "label": "تلگرام: @MahdiSarmad1", "icon": "✈️",
     "url": "https://t.me/MahdiSarmad1", "sort_order": 2, "platform": Platform.TELEGRAM},
    {"key": "instagram", "label": "اینستاگرام: @mahdisarmad", "icon": "📸",
     "url": "https://instagram.com/mahdisarmad", "sort_order": 3},
    {"key": "bale", "label": "بله: @mahdisarmad", "icon": "💬",
     "url": "https://ble.ir/mahdisarmad", "sort_order": 4, "platform": Platform.BALE},
    {"key": "whatsapp", "label": "واتساپ: 09305560950", "icon": "🟢",
     "url": "https://wa.me/989305560950", "sort_order": 5},
    {"key": "linkedin", "label": "لینکدین: mahdisarmad", "icon": "💼",
     "url": "https://linkedin.com/in/mahdisarmad", "sort_order": 6},
    {"key": "email", "label": "ایمیل: mahdisarmad59@gmail.com", "icon": "📧",
     "url": "mailto:mahdisarmad59@gmail.com", "sort_order": 7},
    {"key": "website", "label": "وب‌سایت: mahdisarmad.ir", "icon": "🌐",
     "url": "https://mahdisarmad.ir/", "sort_order": 8},
]


def get(db: Session, link_id: int) -> ContactLink:
    link = db.get(ContactLink, link_id)
    if link is None:
        raise NotFoundError("لینک ارتباطی یافت نشد")
    return link


def get_by_key(db: Session, key: str) -> ContactLink | None:
    return db.scalar(select(ContactLink).where(ContactLink.key == key))


def list_all(db: Session) -> list[ContactLink]:
    return list(db.scalars(select(ContactLink).order_by(ContactLink.sort_order, ContactLink.id)))


def list_active(db: Session, platform: Platform | None = None) -> list[ContactLink]:
    links = list(
        db.scalars(
            select(ContactLink)
            .where(ContactLink.active.is_(True))
            .order_by(ContactLink.sort_order, ContactLink.id)
        )
    )
    if platform is not None:
        # Feature the current platform's own link(s) first.
        links.sort(key=lambda link: (link.platform != platform, link.sort_order, link.id))
    return links


def create(
    db: Session,
    key: str,
    label: str,
    url: str,
    icon: str | None = None,
    platform: Platform | None = None,
    sort_order: int | None = None,
) -> ContactLink:
    key = (key or "").strip()
    label = (label or "").strip()
    url = (url or "").strip()
    if not key or not label or not url:
        raise ValidationError("شناسه، برچسب و آدرس الزامی است")
    if get_by_key(db, key) is not None:
        raise ConflictError("این شناسه قبلاً استفاده شده است")
    if sort_order is None:
        sort_order = max((link.sort_order for link in list_all(db)), default=0) + 1
    link = ContactLink(
        key=key, label=label, url=url, icon=icon, platform=platform, sort_order=sort_order
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def update(
    db: Session,
    link_id: int,
    label: str | None = None,
    url: str | None = None,
    icon: str | None = None,
    active: bool | None = None,
    sort_order: int | None = None,
) -> ContactLink:
    link = get(db, link_id)
    if label is not None:
        label = label.strip()
        if not label:
            raise ValidationError("برچسب الزامی است")
        link.label = label
    if url is not None:
        url = url.strip()
        if not url:
            raise ValidationError("آدرس الزامی است")
        link.url = url
    if icon is not None:
        link.icon = icon or None
    if active is not None:
        link.active = active
    if sort_order is not None:
        link.sort_order = sort_order
    db.commit()
    db.refresh(link)
    return link


def set_active(db: Session, link_id: int, active: bool) -> ContactLink:
    return update(db, link_id, active=active)


def move(db: Session, link_id: int, direction: int) -> None:
    """Swap sort_order with the adjacent link (direction -1 up, +1 down)."""
    links = list_all(db)
    index = next((i for i, link in enumerate(links) if link.id == link_id), None)
    if index is None:
        raise NotFoundError("لینک ارتباطی یافت نشد")
    target = index + (1 if direction > 0 else -1)
    if 0 <= target < len(links):
        a, b = links[index], links[target]
        a.sort_order, b.sort_order = b.sort_order, a.sort_order
        db.commit()


def seed_defaults(db: Session) -> None:
    """Seed the coach's default contact links if missing (idempotent by key)."""
    changed = False
    for row in _DEFAULT_LINKS:
        if get_by_key(db, row["key"]) is None:
            db.add(ContactLink(**row))
            changed = True
    if changed:
        db.commit()
