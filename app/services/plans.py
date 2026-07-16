"""Training / nutrition / custom plan management with file attachments."""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.models import Plan, PlanType
from app.services import notifications
from app.services import persons as persons_service

_TYPE_LABELS = {
    PlanType.TRAINING: "برنامه تمرینی",
    PlanType.NUTRITION: "برنامه تغذیه",
    PlanType.CUSTOM: "برنامه سفارشی",
}

_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp", ".txt", ".docx"}


def type_label(plan_type: PlanType) -> str:
    return _TYPE_LABELS[plan_type]


def get(db: Session, plan_id: int) -> Plan:
    plan = db.get(Plan, plan_id)
    if plan is None:
        raise NotFoundError("برنامه مورد نظر یافت نشد")
    return plan


def list_plans(
    db: Session, person_id: int | None = None, only_active: bool = False
) -> list[Plan]:
    stmt = select(Plan).order_by(Plan.created_at.desc())
    if person_id is not None:
        stmt = stmt.where(Plan.person_id == person_id)
    if only_active:
        stmt = stmt.where(Plan.active.is_(True))
    return list(db.scalars(stmt))


def save_attachment(original_filename: str, content: bytes) -> str:
    """Store an uploaded file under a random name; returns the stored name."""
    extension = Path(original_filename).suffix.lower()
    if extension not in _ALLOWED_EXTENSIONS:
        raise ValidationError("فرمت فایل مجاز نیست (PDF، تصویر یا متن)")
    upload_dir = get_settings().upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{extension}"
    (upload_dir / stored_name).write_bytes(content)
    return stored_name


def attachment_path(plan: Plan) -> Path | None:
    if not plan.file_path:
        return None
    path = get_settings().upload_dir / plan.file_path
    return path if path.is_file() else None


def create(
    db: Session,
    person_id: int,
    plan_type: PlanType,
    title: str,
    description: str | None = None,
    file_path: str | None = None,
    original_filename: str | None = None,
    notify: bool = True,
) -> Plan:
    person = persons_service.get(db, person_id)
    title = title.strip()
    if not title:
        raise ValidationError("عنوان برنامه الزامی است")
    plan = Plan(
        person_id=person_id,
        plan_type=plan_type,
        title=title,
        description=description,
        file_path=file_path,
        original_filename=original_filename,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    if notify:
        notifications.notify_person(
            db,
            person,
            f"{type_label(plan_type)} جدید برای شما ثبت شد 📄\n"
            f"عنوان: {title}\n"
            "برای مشاهده از منوی «📄 برنامه‌های من» استفاده کنید.",
        )
    return plan


def set_active(db: Session, plan_id: int, active: bool) -> Plan:
    plan = get(db, plan_id)
    plan.active = active
    db.commit()
    db.refresh(plan)
    return plan
