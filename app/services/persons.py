"""Person management (clients / coach). No web password — admin auth is by
numeric platform ID (see services.auth)."""

from __future__ import annotations

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.phone import is_valid_phone, normalize_phone
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


def search_stmt(role: Role | None = Role.CLIENT, query: str | None = None) -> Select:
    """Select for a paginated person list, filtered by name / phone / username."""
    stmt = select(Person).order_by(Person.created_at.desc())
    if role is not None:
        stmt = stmt.where(Person.role == role)
    if query:
        needle = f"%{query.strip()}%"
        digits = normalize_phone(query)
        conditions = [Person.name.ilike(needle)]
        if digits:
            conditions.append(Person.phone.ilike(f"%{digits}%"))
        # Match a linked platform username / numeric id too.
        id_match = select(ChannelIdentity.person_id).where(
            or_(
                ChannelIdentity.platform_user_id == query.strip(),
                ChannelIdentity.username.ilike(needle),
            )
        )
        conditions.append(Person.id.in_(id_match))
        stmt = stmt.where(or_(*conditions))
    return stmt


def find_by_platform_id(
    db: Session, platform: Platform, platform_user_id: str
) -> Person | None:
    identity = db.scalar(
        select(ChannelIdentity).where(
            ChannelIdentity.platform == platform,
            ChannelIdentity.platform_user_id == str(platform_user_id).strip(),
        )
    )
    return identity.person if identity else None


def create(
    db: Session,
    name: str,
    phone: str | None = None,
    role: Role = Role.CLIENT,
    note: str | None = None,
) -> Person:
    name = (name or "").strip()
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


def set_active(db: Session, person_id: int, is_active: bool) -> Person:
    """Pause (is_active=False) or reactivate a client."""
    return update(db, person_id, is_active=is_active)
