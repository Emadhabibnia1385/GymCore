"""Program catalog (PlanType) + client program deliveries (PlanAssignment).

Assignments are append-only history: superseded programs are deactivated, never
deleted. A program file may be stored as an internal safe reference under the
upload dir and/or as a platform file_id captured on upload.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models import PlanAssignment, PlanType, Platform
from app.services import notifications
from app.services import persons as persons_service

_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".txt", ".docx", ".xlsx"}


# --- Plan types (catalog) ---


def get_type(db: Session, plan_type_id: int) -> PlanType:
    plan_type = db.get(PlanType, plan_type_id)
    if plan_type is None:
        raise NotFoundError("نوع برنامه یافت نشد")
    return plan_type


def get_type_by_key(db: Session, key: str) -> PlanType | None:
    return db.scalar(select(PlanType).where(PlanType.key == key))


def list_types(db: Session, only_active: bool = False) -> list[PlanType]:
    stmt = select(PlanType).order_by(PlanType.sort_order, PlanType.id)
    if only_active:
        stmt = stmt.where(PlanType.active.is_(True))
    return list(db.scalars(stmt))


def create_type(
    db: Session, title: str, key: str | None = None, sort_order: int | None = None
) -> PlanType:
    title = (title or "").strip()
    if not title:
        raise ValidationError("عنوان نوع برنامه الزامی است")
    key = (key or "").strip() or f"plan-{uuid.uuid4().hex[:8]}"
    if get_type_by_key(db, key) is not None:
        raise ConflictError("این شناسه قبلاً استفاده شده است")
    if sort_order is None:
        sort_order = max((t.sort_order for t in list_types(db)), default=0) + 1
    plan_type = PlanType(key=key, title=title, sort_order=sort_order)
    db.add(plan_type)
    db.commit()
    db.refresh(plan_type)
    return plan_type


def update_type(
    db: Session,
    plan_type_id: int,
    title: str | None = None,
    active: bool | None = None,
    sort_order: int | None = None,
) -> PlanType:
    plan_type = get_type(db, plan_type_id)
    if title is not None:
        title = title.strip()
        if not title:
            raise ValidationError("عنوان نوع برنامه الزامی است")
        plan_type.title = title
    if active is not None:
        plan_type.active = active
    if sort_order is not None:
        plan_type.sort_order = sort_order
    db.commit()
    db.refresh(plan_type)
    return plan_type


def delete_type(db: Session, plan_type_id: int) -> None:
    """Delete a plan type — refused if any assignment references it (deactivate instead)."""
    plan_type = get_type(db, plan_type_id)
    used = db.scalar(
        select(func.count()).select_from(PlanAssignment).where(
            PlanAssignment.plan_type_id == plan_type_id
        )
    )
    if used:
        raise ValidationError("این نوع برنامه در برنامه‌های شاگردان استفاده شده؛ غیرفعالش کن.")
    db.delete(plan_type)
    db.commit()


def seed_defaults(db: Session) -> None:
    """No default plan types — the coach creates their own."""
    return None


# --- Assignments (deliveries) ---


def get_assignment(db: Session, assignment_id: int) -> PlanAssignment:
    assignment = db.get(PlanAssignment, assignment_id)
    if assignment is None:
        raise NotFoundError("برنامه مورد نظر یافت نشد")
    return assignment


def list_assignments(
    db: Session, person_id: int | None = None, only_active: bool = False
) -> list[PlanAssignment]:
    stmt = (
        select(PlanAssignment)
        .order_by(PlanAssignment.created_at.desc(), PlanAssignment.id.desc())
    )
    if person_id is not None:
        stmt = stmt.where(PlanAssignment.person_id == person_id)
    if only_active:
        stmt = stmt.where(PlanAssignment.active.is_(True))
    return list(db.scalars(stmt))


def save_attachment(original_filename: str, content: bytes) -> str:
    """Store an uploaded file under a random name; returns the stored name."""
    extension = Path(original_filename).suffix.lower()
    if extension not in _ALLOWED_EXTENSIONS:
        raise ValidationError("فرمت فایل مجاز نیست (PDF، تصویر، متن یا سند)")
    if len(content) > get_settings().max_upload_bytes:
        raise ValidationError("حجم فایل بیش از حد مجاز است")
    upload_dir = get_settings().upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{extension}"
    (upload_dir / stored_name).write_bytes(content)
    return stored_name


def attachment_path(assignment: PlanAssignment) -> Path | None:
    if not assignment.file_path:
        return None
    path = get_settings().upload_dir / assignment.file_path
    return path if path.is_file() else None


def create_assignment(
    db: Session,
    person_id: int,
    plan_type_id: int,
    title: str | None = None,
    coach_note: str | None = None,
    file_path: str | None = None,
    original_filename: str | None = None,
    platform_file_id: str | None = None,
    file_platform: Platform | None = None,
    created_by: str | None = None,
    notify: bool = True,
) -> PlanAssignment:
    person = persons_service.get(db, person_id)
    plan_type = get_type(db, plan_type_id)
    assignment = PlanAssignment(
        person_id=person_id,
        plan_type_id=plan_type_id,
        title=(title or "").strip() or None,
        coach_note=coach_note,
        file_path=file_path,
        original_filename=original_filename,
        platform_file_id=platform_file_id,
        file_platform=file_platform,
        created_by=created_by,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    if notify:
        notifications.notify_person(
            db,
            person,
            f"{plan_type.title} تازه‌ای برایت آماده شد 📄🟢\n"
            "برای دریافت، از «📄 برنامه‌های من» وارد شو.",
        )
    return assignment


def set_active(db: Session, assignment_id: int, active: bool) -> PlanAssignment:
    assignment = get_assignment(db, assignment_id)
    assignment.active = active
    db.commit()
    db.refresh(assignment)
    return assignment
