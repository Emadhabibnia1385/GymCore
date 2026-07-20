"""Channel identity linking — the bridge between a platform account and a Person.

A Person owns all data; a ChannelIdentity is one platform login. On first
contact from an unknown account we auto-provision a lightweight Person (no
forms, no phone) so the coach can immediately find and manage the client.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.phone import is_valid_phone, normalize_phone
from app.models import ChannelIdentity, Person, Platform, Role
from app.services import persons as persons_service

_PLACEHOLDER_NAMES = {None, "", "کاربر", "کاربر تازه"}


def find_identity(
    db: Session, platform: Platform, platform_user_id: str
) -> ChannelIdentity | None:
    return db.scalar(
        select(ChannelIdentity).where(
            ChannelIdentity.platform == platform,
            ChannelIdentity.platform_user_id == str(platform_user_id),
        )
    )


def find_person(db: Session, platform: Platform, platform_user_id: str) -> Person | None:
    identity = find_identity(db, platform, platform_user_id)
    return identity.person if identity else None


def link_identity(
    db: Session,
    person_id: int,
    platform: Platform,
    platform_user_id: str,
    username: str | None = None,
) -> ChannelIdentity:
    """Attach a platform account to a person (idempotent; re-points if needed)."""
    person = persons_service.get(db, person_id)
    identity = find_identity(db, platform, platform_user_id)
    if identity is not None:
        changed = False
        if identity.person_id != person.id:
            identity.person_id = person.id
            changed = True
        if username and identity.username != username:
            identity.username = username
            changed = True
        if changed:
            db.commit()
        return identity
    identity = ChannelIdentity(
        platform=platform,
        platform_user_id=str(platform_user_id),
        person_id=person.id,
        username=username,
    )
    db.add(identity)
    db.commit()
    db.refresh(identity)
    return identity


def get_or_create_person(
    db: Session,
    platform: Platform,
    platform_user_id: str,
    display_name: str,
    username: str | None = None,
) -> Person:
    """Return the Person for this account, auto-provisioning one on first contact."""
    person = find_person(db, platform, platform_user_id)
    if person is not None:
        # Keep the captured username fresh without touching the coach's edits.
        if username:
            identity = find_identity(db, platform, platform_user_id)
            if identity is not None and identity.username != username:
                identity.username = username
                db.commit()
        return person
    name = (display_name or "").strip() or "کاربر تازه"
    person = persons_service.create(db, name=name, role=Role.CLIENT)
    link_identity(db, person.id, platform, platform_user_id, username=username)
    return person


def link_by_phone(
    db: Session,
    platform: Platform,
    platform_user_id: str,
    raw_phone: str,
    display_name: str,
    username: str | None = None,
) -> Person | None:
    """Register/link this account by phone so Telegram + Bale share one Person.

    Matches an existing Person by phone (e.g. one the coach created), otherwise
    reuses the account's current phone-less Person or creates a new one. Returns
    None if the phone is invalid.
    """
    phone = normalize_phone(raw_phone)
    if not is_valid_phone(phone):
        return None

    target = persons_service.get_by_phone(db, phone)
    identity = find_identity(db, platform, platform_user_id)
    if target is not None:
        person = target
    elif identity is not None and identity.person.phone is None:
        # Reuse the lightweight Person auto-created on an earlier contact.
        person = identity.person
        person.phone = phone
        if display_name and person.name in _PLACEHOLDER_NAMES:
            person.name = display_name.strip()
        db.commit()
    else:
        person = persons_service.create(
            db, name=(display_name or "").strip() or "کاربر", phone=phone, role=Role.CLIENT
        )
    link_identity(db, person.id, platform, platform_user_id, username=username)
    return person


def unlink_identity(db: Session, platform: Platform, platform_user_id: str) -> None:
    identity = find_identity(db, platform, platform_user_id)
    if identity is None:
        raise NotFoundError("این حساب یافت نشد")
    db.delete(identity)
    db.commit()
