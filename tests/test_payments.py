"""Payment balances and immutable corrections."""

from datetime import date

import pytest

from app.core.exceptions import ValidationError
from app.models import PaymentKind
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import payments as payments_service
from app.services import persons as persons_service


def _course(db):
    client = persons_service.create(db, name="کاربر تست")
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db,
        client_id=client.id,
        class_type_id=class_type.id,
        sessions_total=8,
        tuition=1_000_000,
        gym_fee=200_000,
        start_date=date(2026, 7, 1),
    )
    return client, course


def test_balance_outstanding(db):
    client, course = _course(db)
    payments_service.record(
        db,
        person_id=client.id,
        amount=500_000,
        kind=PaymentKind.TUITION,
        paid_at=date(2026, 7, 2),
        course_id=course.id,
        notify=False,
    )
    balance = payments_service.course_balance(db, courses_service.get(db, course.id))
    assert balance["total_due"] == 1_200_000
    assert balance["paid"] == 500_000
    assert balance["outstanding"] == 700_000


def test_negative_correction(db):
    client, course = _course(db)
    payments_service.record(
        db, person_id=client.id, amount=500_000, kind=PaymentKind.TUITION,
        paid_at=date(2026, 7, 2), course_id=course.id, notify=False,
    )
    payments_service.record(
        db, person_id=client.id, amount=-100_000, kind=PaymentKind.TUITION,
        paid_at=date(2026, 7, 3), course_id=course.id, note="اصلاح", notify=False,
    )
    assert payments_service.total_paid(db, course.id) == 400_000


def test_zero_amount_rejected(db):
    client, _ = _course(db)
    with pytest.raises(ValidationError):
        payments_service.record(
            db, person_id=client.id, amount=0, kind=PaymentKind.TUITION,
            paid_at=date(2026, 7, 2), notify=False,
        )


def test_payments_module_has_no_mutators():
    assert not hasattr(payments_service, "update")
    assert not hasattr(payments_service, "delete")
