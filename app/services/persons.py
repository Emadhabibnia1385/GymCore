"""Person management + channel identity linking (used by web and bots)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.phone import is_valid_phone, normalize_phone
from app.core.security import hash_password
from app.models import ChannelIdentity, Person, Platform, Role


def get(db: Session, person_id: int) -> Person:
    person = db.get(Person, person_id)
    if person is None:
        raise NotFoundError("شخص مورد نظر یافت نشد")
    return person


def get_by_phone(db: Session, phone: str) -> Person | None:
    normalized = normalize_phone(phone)
    if not normalized:
        return None
    return db.scalar(select(Person).where(Person.phone == normalized))


def list_persons(
    db: Session, role: Role | None = None, search: str | None = None
) -> list[Person]:
    stmt = select(Person).order_by(Person.created_at.desc())
    if role is not None:
        stmt = stmt.where(Person.role == role)
    if search:
        needle = f"%{search.strip()}%"
        stmt = stmt.where(Person.name.ilike(needle) | Person.phone.ilike(needle))
    return list(db.scalars(stmt))


def create(
    db: Session,
    name: str,
    phone: str | None = None,
    role: Role = Role.CLIENT,
    note: str | None = None,
) -> Person:
    name = name.strip()
    if not name:
        raise ValidationError("نام الزامی است")
    normalized: str | None = None
    if phone:
        normalized = normalize_phone(phone)
        if not is_valid_phone(normalized):
            raise ValidationError("شماره موبایل نامعتبر است")
        if get_by_phone(db, normalized) is not None:
            raise ConflictError("این شماره موبایل قبلاً ثبت شده است")
    person = Person(name=name, phone=normalized, role=role, note=note)
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


def update(
    db: Session,
    person_id: int,
    name: str | None = None,
    phone: str | None = None,
    role: Role | None = None,
    note: str | None = None,
    is_active: bool | None = None,
) -> Person:
    person = get(db, person_id)
    if name is not None:
        name = name.strip()
        if not name:
            raise ValidationError("نام الزامی است")
        person.name = name
    if phone is not None:
        if phone == "":
            person.phone = None
        else:
            normalized = normalize_phone(phone)
            if not is_valid_phone(normalized):
                raise ValidationError("شماره موبایل نامعتبر است")
            existing = get_by_phone(db, normalized)
            if existing is not None and existing.id != person.id:
                raise ConflictError("این شماره موبایل قبلاً ثبت شده است")
            person.phone = normalized
    if role is not None:
        person.role = role
    if note is not None:
        person.note = note or None
    if is_active is not None:
        person.is_active = is_active
    db.commit()
    db.refresh(person)
    return person


def set_web_password(db: Session, person_id: int, password: str) -> Person:
    """Give a person access to the web dashboard."""
    if len(password) < 6:
        raise ValidationError("رمز عبور باید حداقل ۶ کاراکتر باشد")
    person = get(db, person_id)
    person.password_hash = hash_password(password)
    db.commit()
    return person


# --- Channel identities (bot account linking) ---


def find_by_identity(
    db: Session, platform: Platform, platform_user_id: str
) -> Person | None:
    identity = db.scalar(
        select(ChannelIdentity).where(
            ChannelIdentity.platform == platform,
            ChannelIdentity.platform_user_id == str(platform_user_id),
        )
    )
    return identity.person if identity else None


def link_identity(
    db: Session, person_id: int, platform: Platform, platform_user_id: str
) -> ChannelIdentity:
    """Attach a bot account to a person (idempotent)."""
    person = get(db, person_id)
    existing = db.scalar(
        select(ChannelIdentity).where(
            ChannelIdentity.platform == platform,
            ChannelIdentity.platform_user_id == str(platform_user_id),
        )
    )
    if existing is not None:
        if existing.person_id != person.id:
            existing.person_id = person.id
            db.commit()
        return existing
    identity = ChannelIdentity(
        platform=platform, platform_user_id=str(platform_user_id), person_id=person.id
    )
    db.add(identity)
    db.commit()
    db.refresh(identity)
    return identity


def register_from_bot(
    db: Session, platform: Platform, platform_user_id: str, name: str, phone: str
) -> Person:
    """Bot registration flow: link to the existing person with the same
    phone (created earlier by the admin), otherwise create a new client."""
    normalized = normalize_phone(phone)
    if not is_valid_phone(normalized):
        raise ValidationError("شماره موبایل نامعتبر است")
    person = get_by_phone(db, normalized)
    if person is None:
        person = create(db, name=name, phone=normalized, role=Role.CLIENT)
    link_identity(db, person.id, platform, platform_user_id)
    return person
