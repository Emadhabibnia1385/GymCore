"""Class type (catalog) management.

Catalog rows referenced by historical courses are deactivated, never deleted.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models import ClassType

_DEFAULT_CLASS_TYPES = [
    {"key": "bodybuilding", "title": "بدنسازی", "sort_order": 1},
    {"key": "functional", "title": "تمرین فانکشنال", "sort_order": 2},
    {"key": "private", "title": "تمرین خصوصی", "sort_order": 3},
]


def get(db: Session, class_type_id: int) -> ClassType:
    class_type = db.get(ClassType, class_type_id)
    if class_type is None:
        raise NotFoundError("کلاس مورد نظر یافت نشد")
    return class_type


def get_by_key(db: Session, key: str) -> ClassType | None:
    return db.scalar(select(ClassType).where(ClassType.key == key))


def list_class_types(db: Session, only_active: bool = False) -> list[ClassType]:
    stmt = select(ClassType).order_by(ClassType.sort_order, ClassType.id)
    if only_active:
        stmt = stmt.where(ClassType.active.is_(True))
    return list(db.scalars(stmt))


def _generate_key(db: Session, title: str) -> str:
    # ASCII slug of the title if possible, else a stable counter-based key.
    slug = "".join(
        ch if ch.isascii() and (ch.isalnum() or ch == "-") else "-"
        for ch in title.lower()
    )
    slug = "-".join(filter(None, slug.split("-")))
    base = slug or "class"
    candidate = base
    n = 1
    while get_by_key(db, candidate) is not None:
        n += 1
        candidate = f"{base}-{n}"
    return candidate


def create(
    db: Session,
    title: str,
    description: str | None = None,
    key: str | None = None,
    sort_order: int | None = None,
) -> ClassType:
    title = (title or "").strip()
    if not title:
        raise ValidationError("عنوان کلاس الزامی است")
    key = (key or "").strip() or _generate_key(db, title)
    if get_by_key(db, key) is not None:
        raise ConflictError("این شناسه کلاس قبلاً استفاده شده است")
    if sort_order is None:
        current = list_class_types(db)
        sort_order = (max((c.sort_order for c in current), default=0)) + 1
    class_type = ClassType(
        key=key, title=title, description=description, sort_order=sort_order
    )
    db.add(class_type)
    db.commit()
    db.refresh(class_type)
    return class_type


def update(
    db: Session,
    class_type_id: int,
    title: str | None = None,
    description: str | None = None,
    active: bool | None = None,
    sort_order: int | None = None,
) -> ClassType:
    class_type = get(db, class_type_id)
    if title is not None:
        title = title.strip()
        if not title:
            raise ValidationError("عنوان کلاس الزامی است")
        class_type.title = title
    if description is not None:
        class_type.description = description or None
    if active is not None:
        class_type.active = active
    if sort_order is not None:
        class_type.sort_order = sort_order
    db.commit()
    db.refresh(class_type)
    return class_type


def set_active(db: Session, class_type_id: int, active: bool) -> ClassType:
    return update(db, class_type_id, active=active)


def seed_defaults(db: Session) -> None:
    """Seed a few starter class types if none exist (idempotent by key)."""
    changed = False
    for row in _DEFAULT_CLASS_TYPES:
        if get_by_key(db, row["key"]) is None:
            db.add(ClassType(**row))
            changed = True
    if changed:
        db.commit()
