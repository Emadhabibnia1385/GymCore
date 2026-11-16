"""Managing students, courses and classes from the web."""
# ruff: noqa: E501  (request bodies read best on one line)


import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.core import clock
from app.core.config import get_settings
from app.models import CourseStatus, PaymentKind, Platform
from app.services import auth as auth_service
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import identities as identities_service
from app.services import payments as payments_service
from app.services import persons as persons_service
from app.services import web_auth


@pytest.fixture()
def coach(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "web_cookie_secure", False)
    api = TestClient(app)
    person = identities_service.get_or_create_person(db, Platform.TELEGRAM, "111", "مربی")
    auth_service.sync_owner_role(db, Platform.TELEGRAM, "111", person)
    api.cookies.set("gc_session", web_auth.start_session(db, person, "111"))
    return api


def test_students_cannot_manage_anything(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "web_cookie_secure", False)
    student = persons_service.create(db, name="سارا")
    identities_service.link_identity(db, student.id, Platform.TELEGRAM, "5001")
    api = TestClient(app)
    api.cookies.set("gc_session", web_auth.start_session(db, student, "5001"))
    assert api.post("/api/admin/students", json={"name": "x"}).status_code == 403
    assert api.delete(f"/api/admin/students/{student.id}").status_code == 403
    assert api.post("/api/admin/courses", json={}).status_code == 403
    assert api.get("/api/admin/classes").status_code == 403


def test_a_student_is_added_edited_and_a_duplicate_phone_is_refused(db, coach):
    made = coach.post("/api/admin/students", json={"name": "سارا", "phone": "09121111111", "kind": "ONLINE"})
    assert made.status_code == 200
    sid = made.json()["id"]
    assert coach.get(f"/api/admin/students/{sid}").json()["kind"] == "ONLINE"
    coach.patch(f"/api/admin/students/{sid}", json={"name": "سارا احمدی", "phone2": "+447700900123", "kind": "IN_PERSON"})
    profile = coach.get(f"/api/admin/students/{sid}").json()
    assert (profile["name"], profile["phone2"], profile["kind"]) == ("سارا احمدی", "+447700900123", "IN_PERSON")
    clash = coach.post("/api/admin/students", json={"name": "مریم", "phone": "09121111111"})
    assert clash.status_code == 409
    assert coach.post("/api/admin/students", json={"name": "مریم", "phone": "12"}).status_code == 422
    coach.patch(f"/api/admin/students/{sid}", json={"phone2": ""})
    assert coach.get(f"/api/admin/students/{sid}").json()["phone2"] is None


def test_a_student_with_payments_is_not_deleted_from_the_web(db, coach):
    student = persons_service.create(db, name="سارا")
    assert coach.delete(f"/api/admin/students/{student.id}").status_code == 200  # nothing recorded
    paid = persons_service.create(db, name="مریم")
    payments_service.record(db, paid.id, 100_000, PaymentKind.OTHER, clock.today(), notify=False)
    res = coach.delete(f"/api/admin/students/{paid.id}")
    assert res.status_code == 409 and "پرداخت" in res.json()["detail"]
    assert persons_service.get(db, paid.id) is not None


def _new_course(coach, db, **over):
    student = persons_service.create(db, name="سارا")
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    body = {"client_id": student.id, "class_type_id": class_type.id, "sessions_total": 12,
            "tuition": 1_200_000, "allowed_absence": 2, "start_date": clock.today().isoformat(),
            "weekdays": [0, 2, 4], "class_times": {"0": "18:00", "2": "18:00", "4": "19:30", "6": "08:00"}, **over}
    return student, coach.post("/api/admin/courses", json=body)


def test_a_course_is_created_with_its_pattern_and_times(db, coach):
    student, res = _new_course(coach, db)
    assert res.status_code == 200
    course = courses_service.get(db, res.json()["id"])
    assert course.weekdays == "0,2,4" and course.sessions_total == 12
    # A time for a day the class doesn't run on is dropped.
    assert schedule_times(course) == {0: "18:00", 2: "18:00", 4: "19:30"}
    assert coach.get(f"/api/admin/students/{student.id}").json()["courses"][0]["id"] == course.id


def schedule_times(course):
    from app.services import schedule as schedule_service

    return schedule_service.parse_day_times(course.class_times)


def test_a_course_is_refused_for_bad_input(db, coach):
    _, bad_day = _new_course(coach, db, weekdays=[9])
    assert bad_day.status_code == 422
    _, zero = _new_course(coach, db, sessions_total=0)
    assert zero.status_code == 422
    _, ghost = _new_course(coach, db, class_type_id=99999)
    assert ghost.status_code == 404
    res = coach.post("/api/admin/courses", json={"client_id": 99999, "class_type_id": 1, "sessions_total": 5, "start_date": "2026-01-01", "weekdays": [0]})
    assert res.status_code == 404


def test_course_terms_are_edited_and_the_allowance_stays_editable(db, coach):
    _, res = _new_course(coach, db)
    cid = res.json()["id"]
    out = coach.patch(f"/api/admin/courses/{cid}", json={"tuition": 1_500_000, "allowed_absence": 0, "weekdays": [1, 3], "class_times": {"1": "17:00"}}).json()
    assert out["allowed_absence"] == 0 and out["schedule"].startswith("یک‌شنبه 17:00")
    assert courses_service.get(db, cid).tuition == 1_500_000
    assert coach.patch(f"/api/admin/courses/{cid}", json={"allowed_absence": -1}).status_code == 422


def test_a_course_is_finished_renewed_and_deleted(db, coach):
    student, res = _new_course(coach, db)
    cid = res.json()["id"]
    assert coach.post(f"/api/admin/courses/{cid}/status", json={"status": "FINISHED"}).status_code == 200
    assert courses_service.get(db, cid).status == CourseStatus.FINISHED
    renewed = coach.post(f"/api/admin/courses/{cid}/renew")
    assert renewed.status_code == 200 and renewed.json()["id"] != cid
    new = courses_service.get(db, renewed.json()["id"])
    assert (new.sessions_total, new.tuition, new.status) == (12, 1_200_000, CourseStatus.ACTIVE)
    assert coach.delete(f"/api/admin/courses/{new.id}").status_code == 200
    assert coach.delete(f"/api/admin/courses/{new.id}").status_code == 404
    assert student.id  # the student is untouched


def test_the_class_catalog_can_be_managed_and_a_used_class_stays(db, coach):
    made = coach.post("/api/admin/classes", json={"title": "تی‌آر‌ایکس"}).json()["id"]
    assert any(c["title"] == "تی‌آر‌ایکس" for c in coach.get("/api/admin/classes").json())
    coach.patch(f"/api/admin/classes/{made}", json={"title": "TRX", "active": False})
    row = next(c for c in coach.get("/api/admin/classes").json() if c["id"] == made)
    assert row == {"id": made, "title": "TRX", "active": False}
    assert coach.delete(f"/api/admin/classes/{made}").status_code == 200
    _, res = _new_course(coach, db)
    used = courses_service.get(db, res.json()["id"]).class_type_id
    assert coach.delete(f"/api/admin/classes/{used}").status_code == 422  # in use: deactivate instead
    assert coach.post("/api/admin/classes", json={"title": ""}).status_code == 422
