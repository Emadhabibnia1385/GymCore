"""Client requests coming from the bots (class registration, plan orders)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import NotFoundError, ValidationError
from app.models import (
    ClassRegistrationRequest,
    PlanRequest,
    PlanType,
    RequestStatus,
)
from app.services import classes as classes_service
from app.services import notifications
from app.services import persons as persons_service
from app.services import plans as plans_service

# --- Class registration requests ---


def create_class_request(
    db: Session, person_id: int, class_type_id: int, note: str | None = None
) -> ClassRegistrationRequest:
    person = persons_service.get(db, person_id)
    class_type = classes_service.get(db, class_type_id)
    if not class_type.active:
        raise ValidationError("این کلاس در حال حاضر فعال نیست")
    request = ClassRegistrationRequest(
        person_id=person_id, class_type_id=class_type_id, note=note
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    notifications.notify_owner(
        f"🏋️ درخواست ثبت‌نام جدید\n"
        f"نام: {person.name}\n"
        f"موبایل: {person.phone or '-'}\n"
        f"کلاس: {class_type.title}"
    )
    return request


def list_class_requests(
    db: Session, status: RequestStatus | None = None
) -> list[ClassRegistrationRequest]:
    stmt = (
        select(ClassRegistrationRequest)
        .options(
            selectinload(ClassRegistrationRequest.person),
            selectinload(ClassRegistrationRequest.class_type),
        )
        .order_by(ClassRegistrationRequest.created_at.desc())
    )
    if status is not None:
        stmt = stmt.where(ClassRegistrationRequest.status == status)
    return list(db.scalars(stmt))


def decide_class_request(
    db: Session, request_id: int, approve: bool
) -> ClassRegistrationRequest:
    request = db.get(ClassRegistrationRequest, request_id)
    if request is None:
        raise NotFoundError("درخواست مورد نظر یافت نشد")
    if request.status != RequestStatus.PENDING:
        raise ValidationError("این درخواست قبلاً بررسی شده است")
    request.status = RequestStatus.APPROVED if approve else RequestStatus.REJECTED
    request.decided_at = datetime.now(UTC)
    db.commit()
    db.refresh(request)

    if approve:
        text = (
            f"درخواست ثبت‌نام شما در کلاس «{request.class_type.title}» تایید شد ✅\n"
            "مربی به‌زودی دوره شما را فعال می‌کند."
        )
    else:
        text = f"درخواست ثبت‌نام شما در کلاس «{request.class_type.title}» رد شد."
    notifications.notify_person(db, request.person, text)
    return request


# --- Plan requests ---


def create_plan_request(
    db: Session, person_id: int, plan_type: PlanType, note: str | None = None
) -> PlanRequest:
    person = persons_service.get(db, person_id)
    request = PlanRequest(person_id=person_id, plan_type=plan_type, note=note)
    db.add(request)
    db.commit()
    db.refresh(request)
    notifications.notify_owner(
        f"📋 سفارش برنامه جدید\n"
        f"نام: {person.name}\n"
        f"موبایل: {person.phone or '-'}\n"
        f"نوع: {plans_service.type_label(plan_type)}\n"
        f"توضیحات: {note or '-'}"
    )
    return request


def list_plan_requests(
    db: Session, status: RequestStatus | None = None
) -> list[PlanRequest]:
    stmt = (
        select(PlanRequest)
        .options(selectinload(PlanRequest.person))
        .order_by(PlanRequest.created_at.desc())
    )
    if status is not None:
        stmt = stmt.where(PlanRequest.status == status)
    return list(db.scalars(stmt))


def decide_plan_request(db: Session, request_id: int, approve: bool) -> PlanRequest:
    request = db.get(PlanRequest, request_id)
    if request is None:
        raise NotFoundError("درخواست مورد نظر یافت نشد")
    if request.status != RequestStatus.PENDING:
        raise ValidationError("این درخواست قبلاً بررسی شده است")
    request.status = RequestStatus.APPROVED if approve else RequestStatus.REJECTED
    request.decided_at = datetime.now(UTC)
    db.commit()
    db.refresh(request)

    label = plans_service.type_label(request.plan_type)
    if approve:
        text = f"سفارش {label} شما تایید شد ✅\nبرنامه پس از آماده‌سازی برای شما ارسال می‌شود."
    else:
        text = f"سفارش {label} شما رد شد."
    notifications.notify_person(db, request.person, text)
    return request
