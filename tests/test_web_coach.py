"""The coach's daily work through the web API — and that students can't touch it."""
# ruff: noqa: E501  (request bodies read best on one line)

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.core import clock
from app.core.config import get_settings
from app.models import Platform
from app.services import attendance as attendance_service
from app.services import auth as auth_service
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import identities as identities_service
from app.services import persons as persons_service
from app.services import schedule as schedule_service
from app.services import web_auth


@pytest.fixture()
def coach(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "web_cookie_secure", False)
    api = TestClient(app)
    person = identities_service.get_or_create_person(db, Platform.TELEGRAM, "111", "مربی")
    auth_service.sync_owner_role(db, Platform.TELEGRAM, "111", person)
    api.cookies.set("gc_session", web_auth.start_session(db, person, "111"))
    return api


def _course(db, name="سارا", total=60, tuition=600_000):
    student = persons_service.create(db, name=name)
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    return courses_service.create(
        db, client_id=student.id, class_type_id=class_type.id, sessions_total=total,
        tuition=tuition, allowed_absence=2, start_date=clock.today() - timedelta(days=30),
        weekdays="0,1,2,3,4,5,6", class_times="0@18:00,1@18:00,2@18:00,3@18:00,4@18:00,5@18:00,6@18:00",
    )


def test_students_cannot_use_any_coach_action(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "web_cookie_secure", False)
    student = persons_service.create(db, name="سارا")
    identities_service.link_identity(db, student.id, Platform.TELEGRAM, "5001")
    api = TestClient(app)
    api.cookies.set("gc_session", web_auth.start_session(db, student, "5001"))
    assert api.get("/api/admin/attendance/day").status_code == 403
    assert api.post("/api/admin/attendance", json={}).status_code == 403
    assert api.post("/api/admin/payments", json={}).status_code == 403
    assert api.post("/api/admin/expenses", json={}).status_code == 403
    assert api.get("/api/admin/finance/month").status_code == 403


def test_the_day_view_lists_who_trains_today_and_marks_them(db, coach):
    course = _course(db)
    day = coach.get("/api/admin/attendance/day").json()
    assert day["is_today"] and day["rows"][0]["student"] == "سارا"
    assert day["rows"][0]["status"] is None and day["rows"][0]["time"] == "18:00"
    res = coach.post("/api/admin/attendance", json={
        "course_id": course.id, "date": clock.today().isoformat(), "status": "PRESENT"})
    assert res.status_code == 200
    again = coach.get("/api/admin/attendance/day").json()["rows"][0]
    assert again["status"] == "PRESENT" and again["label"] == "حاضر"
    # Attendance is append-only: a correction is a new event, the latest wins.
    coach.post("/api/admin/attendance", json={
        "course_id": course.id, "date": clock.today().isoformat(), "status": "ABSENT_ALLOWED"})
    assert coach.get("/api/admin/attendance/day").json()["rows"][0]["status"] == "ABSENT_ALLOWED"
    assert len(attendance_service.list_for_course(db, course.id)) == 2


def test_a_future_session_a_move_status_and_a_year_typo_are_refused(db, coach):
    course = _course(db)
    tomorrow = (clock.today() + timedelta(days=1)).isoformat()
    future = coach.post("/api/admin/attendance", json={
        "course_id": course.id, "date": tomorrow, "status": "PRESENT"})
    assert future.status_code == 422
    moved = coach.post("/api/admin/attendance", json={
        "course_id": course.id, "date": clock.today().isoformat(), "status": "MOVED"})
    assert moved.status_code == 422
    typo = coach.post("/api/admin/attendance/move", json={
        "course_id": course.id, "date": clock.today().isoformat(),
        "new_date": (clock.today() - timedelta(days=365)).isoformat()})
    assert typo.status_code == 422 and "سال" in typo.json()["detail"]


def test_a_session_can_be_moved_and_it_follows_on_the_grid(db, coach):
    course = _course(db)
    first = schedule_service.build(db, course)[0].date
    target = clock.today() + timedelta(days=10)
    res = coach.post("/api/admin/attendance/move", json={
        "course_id": course.id, "date": first.isoformat(), "new_date": target.isoformat()})
    assert res.status_code == 200
    grid = coach.get(f"/api/admin/courses/{course.id}").json()["slots"]
    assert first.isoformat() not in [s["iso"] for s in grid]


def test_a_payment_is_recorded_and_corrected_with_a_negative_one(db, coach):
    course = _course(db)
    body = {"person_id": course.client_id, "amount": 400_000, "kind": "TUITION",
            "paid_at": clock.today().isoformat(), "course_id": course.id}
    assert coach.post("/api/admin/payments", json=body).status_code == 200
    assert coach.get("/api/admin/payments/owing").json()[0]["amount"] == 200_000
    coach.post("/api/admin/payments", json={**body, "amount": -100_000, "note": "اصلاح"})
    assert coach.get("/api/admin/payments/owing").json()[0]["amount"] == 300_000
    assert coach.post("/api/admin/payments", json={**body, "amount": 0}).status_code == 422


def test_a_payment_cannot_be_booked_to_another_students_course(db, coach):
    mine, other = _course(db, "سارا"), _course(db, "مریم")
    res = coach.post("/api/admin/payments", json={
        "person_id": mine.client_id, "amount": 1000, "kind": "TUITION",
        "paid_at": clock.today().isoformat(), "course_id": other.id})
    assert res.status_code == 404


def test_expenses_feed_the_monthly_report_and_the_year(db, coach):
    course = _course(db)
    coach.post("/api/admin/payments", json={
        "person_id": course.client_id, "amount": 500_000, "kind": "TUITION",
        "paid_at": clock.today().isoformat(), "course_id": course.id})
    assert coach.post("/api/admin/expenses", json={
        "amount": 150_000, "category": "BILLS", "spent_at": clock.today().isoformat()}).status_code == 200
    month = coach.get("/api/admin/finance/month").json()
    assert (month["income"], month["expenses"], month["net"]) == (500_000, 150_000, 350_000)
    assert month["income_by_kind"] == [{"key": "TUITION", "label": "شهریه", "amount": 500_000}]
    assert month["expenses_by_category"][0]["label"] == "قبوض" and month["next"] is None
    year = coach.get(f"/api/admin/finance/year?jy={month['jy']}").json()
    assert year["net"] == 350_000 and len(year["rows"]) == 12
    listed = coach.get(f"/api/admin/finance/expenses?jy={month['jy']}&jm={month['jm']}").json()
    assert listed[0]["amount"] == 150_000
    # A date a year back (the typo nobody sees), zero, and a bad month are refused.
    old = (clock.today() - timedelta(days=366)).isoformat()
    assert coach.post("/api/admin/expenses", json={"amount": 1000, "category": "RENT", "spent_at": old}).status_code == 422
    assert coach.post("/api/admin/expenses", json={"amount": 0, "category": "RENT", "spent_at": clock.today().isoformat()}).status_code == 422
    assert coach.get("/api/admin/finance/expenses?jy=1405&jm=13").status_code == 422
