"""API-level guarantees: attendance append-only, payments immutable."""

from datetime import date

import pytest

from app.core.exceptions import ValidationError
from app.models import PaymentKind
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import payments as payments_service
from app.services import persons as persons_service


@pytest.fixture()
def setup_ids(db, unique_phone):
    person = persons_service.create(db, name="مهدی احمدی", phone=unique_phone)
    class_type = classes_service.create(db, title="کراس‌فیت")
    course = courses_service.create(
        db,
        client_id=person.id,
        class_type_id=class_type.id,
        sessions_total=10,
        tuition=1_000_000,
        gym_fee=0,
        start_date=date(2026, 7, 1),
    )
    return {"person_id": person.id, "course_id": course.id}


def test_attendance_has_no_update_or_delete_routes(client, admin_headers, setup_ids):
    course_id = setup_ids["course_id"]
    response = client.post(
        f"/api/v1/courses/{course_id}/attendance",
        headers=admin_headers,
        json={
            "course_id": course_id,
            "session_date": "2026-07-02",
            "status": "PRESENT",
        },
    )
    assert response.status_code == 201
    event_id = response.json()["id"]

    # Append-only: no mutation route exists at all (404 = no such path,
    # 405 = path exists but method not allowed — both prove immutability).
    base = f"/api/v1/courses/{course_id}/attendance"
    assert client.delete(f"{base}/{event_id}", headers=admin_headers).status_code in (404, 405)
    assert client.patch(f"{base}/{event_id}", headers=admin_headers).status_code in (404, 405)
    assert client.delete(base, headers=admin_headers).status_code == 405


def test_payments_have_no_update_or_delete_routes(client, admin_headers, setup_ids):
    response = client.post(
        "/api/v1/payments",
        headers=admin_headers,
        json={
            "person_id": setup_ids["person_id"],
            "course_id": setup_ids["course_id"],
            "amount": 500000,
            "kind": "TUITION",
            "paid_at": "2026-07-02",
        },
    )
    assert response.status_code == 201
    payment_id = response.json()["id"]

    assert client.delete(
        f"/api/v1/payments/{payment_id}", headers=admin_headers
    ).status_code in (404, 405)
    assert client.patch(
        f"/api/v1/payments/{payment_id}", headers=admin_headers
    ).status_code in (404, 405)
    assert client.delete("/api/v1/payments", headers=admin_headers).status_code == 405


def test_payment_business_rules(db, setup_ids):
    with pytest.raises(ValidationError):
        payments_service.record(
            db,
            person_id=setup_ids["person_id"],
            amount=0,  # zero amount is meaningless
            kind=PaymentKind.TUITION,
            paid_at=date(2026, 7, 2),
        )

    # Payment against someone else's course is rejected.
    other = persons_service.create(db, name="نادر قاسمی", phone="09125555555")
    with pytest.raises(ValidationError):
        payments_service.record(
            db,
            person_id=other.id,
            amount=1000,
            kind=PaymentKind.TUITION,
            paid_at=date(2026, 7, 2),
            course_id=setup_ids["course_id"],
        )

    # Correction pattern: negative amount is allowed.
    payment = payments_service.record(
        db,
        person_id=setup_ids["person_id"],
        amount=-200_000,
        kind=PaymentKind.TUITION,
        paid_at=date(2026, 7, 3),
        course_id=setup_ids["course_id"],
        note="اصلاح ثبت اشتباه",
    )
    assert payment.amount == -200_000


def test_client_cannot_access_admin_endpoints(client, db, setup_ids):
    person_id = setup_ids["person_id"]
    persons_service.set_web_password(db, person_id, "client-pass")
    person = persons_service.get(db, person_id)

    login = client.post(
        "/api/v1/auth/login",
        json={"phone": person.phone, "password": "client-pass"},
    )
    assert login.status_code == 200
    client.cookies.clear()  # rely on the explicit Bearer header only
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Admin-only endpoints are forbidden for clients.
    assert client.get("/api/v1/persons", headers=headers).status_code == 403
    # But clients see their own courses.
    response = client.get("/api/v1/courses", headers=headers)
    assert response.status_code == 200
    assert all(c["client_id"] == person_id for c in response.json())
