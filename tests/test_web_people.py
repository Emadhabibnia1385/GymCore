"""The web panel for students (their own world) and for the coach (the roster)."""

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.core import clock
from app.models import AttendanceStatus, PaymentKind, Platform, StudentType
from app.services import attendance as attendance_service
from app.services import auth as auth_service
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import crm as crm_service
from app.services import identities as identities_service
from app.services import packages as packages_service
from app.services import payments as payments_service
from app.services import persons as persons_service
from app.services import plans as plans_service
from app.services import schedule as schedule_service
from app.services import web_auth
from tests.fakes import FakeBotClient

OWNER = "111"


@pytest.fixture()
def api(db):
    return TestClient(app)


def _sign_in(db, api, person, telegram_id):
    token = web_auth.start_session(db, person, str(telegram_id))
    api.cookies.set("gc_session", token)


def _student(db, name="سارا", telegram_id="5001", **kwargs):
    person = persons_service.create(db, name=name, **kwargs)
    identities_service.link_identity(db, person.id, Platform.TELEGRAM, telegram_id)
    return person


def _course(db, person, sessions_total=6, tuition=600_000):
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    return courses_service.create(
        db, client_id=person.id, class_type_id=class_type.id, sessions_total=sessions_total,
        tuition=tuition, allowed_absence=2, start_date=clock.today() - timedelta(days=30),
        weekdays="0,2,4",
    )


def _coach(db, api):
    coach = identities_service.get_or_create_person(db, Platform.TELEGRAM, OWNER, "مربی")
    auth_service.sync_owner_role(db, Platform.TELEGRAM, OWNER, coach)
    _sign_in(db, api, coach, OWNER)


# --- the student's own world ---


def test_a_student_sees_their_subscription_and_grid_but_no_money(db, api):
    sara = _student(db)
    course = _course(db, sara)
    first_day = schedule_service.build(db, course)[0].date
    attendance_service.record(db, course.id, first_day, AttendanceStatus.PRESENT, notify=False)
    _sign_in(db, api, sara, "5001")
    home = api.get("/api/me/home").json()
    assert home["name"] == "سارا" and home["active_course"]["remaining"] == 5
    detail = api.get(f"/api/me/courses/{course.id}").json()
    assert detail["consumed"] == 1 and len(detail["slots"]) == 6
    assert detail["slots"][0]["label"] == "حاضر" and detail["slots"][0]["session_no"] == 1
    assert "tuition" not in detail and "paid" not in detail  # a student sees no money


def test_a_student_cannot_open_anothers_course_or_package(db, api):
    sara, maryam = _student(db), _student(db, "مریم", "5002")
    theirs = _course(db, maryam)
    package = packages_service.create(db, "پکیج مریم")
    packages_service.add_item(db, package.id, kind="text", text="x")
    packages_service.assign(db, package.id, [maryam.id], notify=False)
    _sign_in(db, api, sara, "5001")
    assert api.get(f"/api/me/courses/{theirs.id}").status_code == 404
    assert api.get(f"/api/me/packages/{package.id}").status_code == 404
    assert api.get("/api/me/courses/999999").status_code == 404  # same answer: nothing leaks


def test_programs_and_packages_are_listed_and_a_revoked_package_vanishes(db, api):
    sara = _student(db, student_type=StudentType.ONLINE)
    diet = plans_service.create_type(db, title="تغذیه")
    plans_service.create_assignment(
        db, person_id=sara.id, plan_type_id=diet.id, coach_note="هفته اول", notify=False
    )
    package = packages_service.create(db, "پکیج کاهش وزن")
    packages_service.add_item(db, package.id, kind="text", text="آب بنوش")
    packages_service.assign(db, package.id, [sara.id], notify=False)
    _sign_in(db, api, sara, "5001")
    (program,) = api.get("/api/me/programs").json()
    assert program["title"] == "تغذیه" and program["note"] == "هفته اول"
    (listed,) = api.get("/api/me/packages").json()
    assert listed["items"] == 1
    assert api.get(f"/api/me/packages/{package.id}").json()["item_list"][0]["text"] == "آب بنوش"
    packages_service.set_active(db, package.id, False)
    assert api.get("/api/me/packages").json() == []
    assert api.get(f"/api/me/packages/{package.id}").status_code == 404


def test_a_program_file_is_sent_through_the_bot_to_the_students_telegram(db, api, monkeypatch):
    sara = _student(db)
    diet = plans_service.create_type(db, title="تغذیه")
    program = plans_service.create_assignment(
        db, person_id=sara.id, plan_type_id=diet.id, coach_note="متن برنامه",
        platform_file_id="DOC1", file_platform=Platform.TELEGRAM, file_kind="document",
        notify=False,
    )
    fake = FakeBotClient(Platform.TELEGRAM)
    monkeypatch.setattr("app.bots.common.client.build_client", lambda platform: fake)
    _sign_in(db, api, sara, "5001")
    assert api.post(f"/api/me/programs/{program.id}/send").status_code == 200
    assert fake.sent[0]["method"] == "send_document_id" and fake.sent[0]["chat_id"] == "5001"
    # Another student's program is a 404, and so is a made-up one.
    other = _student(db, "مریم", "5002")
    _sign_in(db, api, other, "5002")
    assert api.post(f"/api/me/programs/{program.id}/send").status_code == 404


def test_a_student_asks_for_a_course_and_it_reaches_the_coachs_follow_ups(db, api):
    sara = _student(db)
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    _sign_in(db, api, sara, "5001")
    assert [c["id"] for c in api.get("/api/me/classes").json()] == [class_type.id]
    res = api.post("/api/me/course-request", json={"class_type_id": class_type.id, "note": "عصرها"})
    assert res.status_code == 200
    (follow_up,) = crm_service.list_due(db)
    assert follow_up.person_id == sara.id and "عصرها" in follow_up.note
    again = api.post("/api/me/course-request", json={})
    assert again.status_code == 409  # one open request at a time
    assert api.post("/api/me/course-request", json={"class_type_id": 99999}).status_code == 404


# --- the coach's roster ---


def test_students_cannot_reach_the_coachs_routes(db, api):
    sara = _student(db)
    _sign_in(db, api, sara, "5001")
    for path in ("/api/admin/students", f"/api/admin/students/{sara.id}", "/api/admin/courses/1"):
        assert api.get(path).status_code == 403
    assert TestClient(app).get("/api/admin/students").status_code == 401  # not signed in at all


def test_the_roster_orders_by_who_needs_a_call_and_splits_by_kind(db, api):
    low, plenty = _student(db, "کم‌جلسه", "5001"), _student(db, "پرجلسه", "5002")
    _course(db, low, sessions_total=2)
    _course(db, plenty, sessions_total=10)
    ended = _student(db, "تمام‌کرده", "5003")
    done = _course(db, ended, sessions_total=1)
    attendance_service.record(
        db, done.id, clock.today() - timedelta(days=28), AttendanceStatus.PRESENT, notify=False
    )
    persons_service.create(db, name="بی‌دوره")
    _student(db, "آنلاین", "5004", student_type=StudentType.ONLINE)
    _coach(db, api)
    data = api.get("/api/admin/students").json()
    assert (data["in_person"], data["online"]) == (4, 1)
    assert [r["name"] for r in data["rows"]] == [
        "کم‌جلسه", "پرجلسه", "تمام‌کرده", "بی‌دوره", "آنلاین"
    ]
    assert [r["state"] for r in data["rows"]] == ["active", "active", "ended", "none", "online"]
    online = api.get("/api/admin/students?kind=ONLINE").json()
    assert [r["name"] for r in online["rows"]] == ["آنلاین"]
    assert [r["name"] for r in api.get("/api/admin/students?q=تمام").json()["rows"]] == ["تمام‌کرده"]
    assert api.get("/api/admin/students?kind=EVIL").status_code == 422


def test_a_student_profile_shows_courses_money_and_programs(db, api):
    sara = _student(db, phone="09121111111")
    course = _course(db, sara, tuition=600_000)
    payments_service.record(
        db, sara.id, 250_000, PaymentKind.TUITION, clock.today(), course_id=course.id,
        notify=False,
    )
    _coach(db, api)
    profile = api.get(f"/api/admin/students/{sara.id}").json()
    assert profile["phone"] == "09121111111" and profile["on_telegram"] is True
    assert (profile["paid"], profile["owing"]) == (250_000, 350_000)
    assert profile["payments"][0]["amount"] == 250_000
    assert profile["courses"][0]["id"] == course.id
    assert api.get(f"/api/admin/courses/{course.id}").json()["slots"]
    assert api.get("/api/admin/students/999999").status_code == 404
    coach_id = identities_service.find_person(db, Platform.TELEGRAM, OWNER).id
    assert api.get(f"/api/admin/students/{coach_id}").status_code == 404


def test_the_student_list_carries_phone_class_and_what_is_owed(db):
    from fastapi.testclient import TestClient

    from app.api.main import app
    from app.core import clock
    from app.core.config import get_settings
    from app.services import classes as classes_service
    from app.services import courses as courses_service

    get_settings().web_cookie_secure = False
    get_settings().web_dev_login = True
    try:
        client = TestClient(app)
        assert client.post("/api/auth/dev").status_code == 200
        student = persons_service.create(db, name="سارا", phone="09120000000")
        kind = classes_service.list_class_types(db, only_active=True)[0]
        courses_service.create(
            db, client_id=student.id, class_type_id=kind.id, sessions_total=12, tuition=900_000,
            start_date=clock.today(), weekdays="0", class_times="0@18:00",
        )
        row = client.get("/api/admin/students").json()["rows"][0]
        assert (row["phone"], row["class_title"], row["total"], row["owing"]) == (
            "09120000000", kind.title, 12, 900_000)
    finally:
        get_settings().web_dev_login = False


def test_the_course_page_carries_what_was_paid_and_what_is_left(db):
    from fastapi.testclient import TestClient

    from app.api.main import app
    from app.core import clock
    from app.core.config import get_settings
    from app.models import PaymentKind
    from app.services import classes as classes_service
    from app.services import courses as courses_service
    from app.services import payments as payments_service

    get_settings().web_cookie_secure = False
    get_settings().web_dev_login = True
    try:
        client = TestClient(app)
        assert client.post("/api/auth/dev").status_code == 200
        student = persons_service.create(db, name="سارا")
        kind = classes_service.list_class_types(db, only_active=True)[0]
        course = courses_service.create(
            db, client_id=student.id, class_type_id=kind.id, sessions_total=12, tuition=900_000,
            start_date=clock.today(), weekdays="0", class_times="0@18:00",
        )
        payments_service.record(db, student.id, 300_000, PaymentKind.TUITION, clock.today(),
                                course_id=course.id, notify=False)
        data = client.get(f"/api/admin/courses/{course.id}").json()
        assert (data["paid"], data["outstanding"]) == (300_000, 600_000)
        assert [p["amount"] for p in data["payments"]] == [300_000]
    finally:
        get_settings().web_dev_login = False
