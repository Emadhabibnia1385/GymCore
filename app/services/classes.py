"""Class type management."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models import ClassType


def get(db: Session, class_type_id: int) -> ClassType:
    class_type = db.get(ClassType, class_type_id)
    if class_type is None:
        raise NotFoundError("کلاس مورد نظر یافت نشد")
    return class_type


def list_class_types(db: Session, only_active: bool = False) -> list[ClassType]:
    stmt = select(ClassType).order_by(ClassType.sort_order, ClassType.id)
    if only_active:
        stmt = stmt.where(ClassType.active.is_(True))
    return list(db.scalars(stmt))


def create(
    db: Session, title: str, description: str | None = None, sort_order: int = 0
) -> ClassType:
    title = title.strip()
    if not title:
        raise ValidationError("عنوان کلاس الزامی است")
    class_type = ClassType(title=title, description=description, sort_order=sort_order)
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
