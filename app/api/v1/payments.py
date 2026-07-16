"""Payment endpoints. History is immutable — no update/delete routes."""

from fastapi import APIRouter

from app.api.deps import AdminPerson, CurrentPerson, DbDep
from app.models import Role
from app.schemas.entities import PaymentCreateIn, PaymentOut
from app.services import payments as payments_service

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("", response_model=list[PaymentOut])
def list_payments(
    db: DbDep,
    person: CurrentPerson,
    person_id: int | None = None,
    course_id: int | None = None,
) -> list[PaymentOut]:
    # Non-admins can only see their own payments.
    if person.role != Role.ADMIN:
        person_id = person.id
    return [
        PaymentOut.model_validate(p)
        for p in payments_service.list_payments(
            db, person_id=person_id, course_id=course_id
        )
    ]


@router.post("", response_model=PaymentOut, status_code=201)
def record_payment(body: PaymentCreateIn, db: DbDep, _: AdminPerson) -> PaymentOut:
    payment = payments_service.record(
        db,
        person_id=body.person_id,
        amount=body.amount,
        kind=body.kind,
        paid_at=body.paid_at,
        course_id=body.course_id,
        method=body.method,
        note=body.note,
    )
    return PaymentOut.model_validate(payment)
