"""Payment recording — history is immutable.

There is deliberately no update or delete function in this module.
Corrections are recorded as new payments with negative amounts.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models import Payment, PaymentKind
from app.services import courses as courses_service
from app.services import notifications
from app.services import persons as persons_service

_KIND_LABELS = {
    PaymentKind.TUITION: "شهریه",
    PaymentKind.GYM_FEE: "ورودی باشگاه",
    PaymentKind.OTHER: "سایر",
}


def kind_label(kind: PaymentKind) -> str:
    return _KIND_LABELS[kind]


def list_payments(
    db: Session, person_id: int | None = None, course_id: int | None = None
) -> list[Payment]:
    stmt = select(Payment).order_by(Payment.paid_at.desc(), Payment.id.desc())
    if person_id is not None:
        stmt = stmt.where(Payment.person_id == person_id)
    if course_id is not None:
        stmt = stmt.where(Payment.course_id == course_id)
    return list(db.scalars(stmt))


def total_paid(db: Session, course_id: int) -> int:
    return (
        db.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(
                Payment.course_id == course_id
            )
        )
        or 0
    )


def record(
    db: Session,
    person_id: int,
    amount: int,
    kind: PaymentKind,
    paid_at: date,
    course_id: int | None = None,
    method: str | None = None,
    note: str | None = None,
    notify: bool = True,
) -> Payment:
    person = persons_service.get(db, person_id)
    if amount == 0:
        raise ValidationError("مبلغ پرداخت نمی‌تواند صفر باشد")
    if course_id is not None:
        course = courses_service.get(db, course_id)
        if course.client_id != person.id:
            raise ValidationError("این دوره متعلق به این شخص نیست")

    payment = Payment(
        person_id=person_id,
        course_id=course_id,
        amount=amount,
        kind=kind,
        method=method,
        paid_at=paid_at,
        note=note,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    if notify and amount > 0:
        notifications.notify_person(
            db,
            person,
            f"پرداخت شما ثبت شد ✅\n"
            f"مبلغ: {amount:,} تومان\n"
            f"بابت: {kind_label(kind)}\n"
            f"تاریخ: {paid_at.isoformat()}",
        )
    return payment
