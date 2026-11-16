"""The coach's yearly report, through the real FastAPI app."""

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.core import clock
from app.core.config import get_settings
from app.models import AttendanceStatus, ExpenseCategory, PaymentKind
from app.services import attendance as attendance_service
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import finance as finance_service
from app.services import payments as payments_service
from app.services import persons as persons_service


@pytest.fixture()
def coach(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "web_cookie_secure", False)
    monkeypatch.setattr(get_settings(), "web_dev_login", True)
    client = TestClient(app)
    assert client.post("/api/auth/dev").status_code == 200
    return client


def test_only_the_coach_reads_reports(db):
    assert TestClient(app).get("/api/admin/reports").status_code == 401


def test_an_empty_gym_still_reports(db, coach):
    data = coach.get("/api/admin/reports").json()
    assert data["kpis"]["students"] == 0 and data["kpis"]["income_year"] == 0
    assert len(data["months"]) == 12 and len(data["weeks"]) == 8
    assert data["attendance"]["rate"] == 0 and data["debtors"] == []


def test_the_report_adds_up_the_gyms_real_numbers(db, coach):
    student = persons_service.create(db, name="سارا")
    kind = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=student.id, class_type_id=kind.id, sessions_total=2, tuition=1_000_000,
        start_date=clock.today(), weekdays="0,1,2,3,4,5,6",
        class_times="0@18:00,1@18:00,2@18:00,3@18:00,4@18:00,5@18:00,6@18:00",
    )
    payments_service.record(db, student.id, 400_000, PaymentKind.TUITION, clock.today(),
                            course_id=course.id, notify=False)
    finance_service.record_expense(db, 150_000, ExpenseCategory.BILLS, clock.today())
    attendance_service.record(db, course.id, clock.today(), AttendanceStatus.PRESENT)

    data = coach.get("/api/admin/reports").json()
    k = data["kpis"]
    assert k["students"] == 1 and k["courses_active"] == 1
    assert (k["income_year"], k["expenses_year"], k["net_year"]) == (400_000, 150_000, 250_000)
    assert k["owing_total"] == 600_000 and k["average_payment"] == 400_000
    assert k["ending_soon"] == 1  # two sessions bought, one used
    assert data["attendance"]["present"] == 1 and data["attendance"]["rate"] == 100.0
    assert data["classes"][0]["income"] == 400_000 and data["classes"][0]["active_courses"] == 1
    assert data["income_by_kind"] == [{"key": "TUITION", "label": "شهریه", "amount": 400_000}]
    assert data["debtors"][0]["student"] == "سارا" and data["ending_soon"][0]["remaining"] == 1
    assert sum(w["present"] for w in data["weeks"]) == 1
    assert sum(m["new_students"] for m in data["months"]) == 1


def test_the_sheet_lays_a_month_out_by_day_and_student(db, coach):
    student = persons_service.create(db, name="سارا")
    kind = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=student.id, class_type_id=kind.id, sessions_total=12, tuition=1_000_000,
        start_date=clock.today(), weekdays="0,1,2,3,4,5,6",
        class_times="0@18:00,1@18:00,2@18:00,3@18:00,4@18:00,5@18:00,6@18:00",
    )
    attendance_service.record(db, course.id, clock.today(), AttendanceStatus.PRESENT)
    payments_service.record(db, student.id, 400_000, PaymentKind.TUITION, clock.today(),
                            course_id=course.id, notify=False)
    sheet = coach.get("/api/admin/attendance/sheet").json()
    assert 29 <= len(sheet["days"]) <= 31 and sheet["next"] is None
    assert [c["student"] for c in sheet["columns"]] == ["سارا"]
    cell = sheet["cells"][str(course.id)][clock.today().isoformat()]
    assert cell == {"status": "PRESENT", "session_no": 1, "paid": True}
    assert sum(1 for d in sheet["days"] if d["friday"]) in (4, 5)
    assert sum(1 for d in sheet["days"] if d["today"]) == 1
    last = coach.get("/api/admin/attendance/sheet?year=1390&month=1").json()
    assert last["columns"] == [] and len(last["days"]) == 31  # a month before anyone started


def test_money_over_a_month_a_year_a_run_of_days_and_a_custom_range(db, coach):
    from datetime import timedelta

    student = persons_service.create(db, name="سارا")
    kind = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=student.id, class_type_id=kind.id, sessions_total=12, tuition=1_000_000,
        start_date=clock.today(), weekdays="0", class_times="0@18:00",
    )
    today = clock.today()
    payments_service.record(db, student.id, 400_000, PaymentKind.TUITION, today,
                            course_id=course.id, notify=False)
    finance_service.record_expense(db, 150_000, ExpenseCategory.BILLS, today)

    month = coach.get("/api/admin/finance/period").json()
    assert (month["kind"], month["income"], month["expenses"], month["net"]) == (
        "month", 400_000, 150_000, 250_000)
    assert month["next_month"] is None and month["previous"]["income"] == 0
    assert month["expense_rows"][0]["amount"] == 150_000
    assert month["income_by_kind"][0]["amount"] == 400_000

    last = coach.get("/api/admin/finance/period?last=7").json()
    assert last["kind"] == "last" and last["days"] == 7 and last["income"] == 400_000
    assert len(last["series"]) == 7 and sum(p["income"] for p in last["series"]) == 400_000

    year = coach.get(f"/api/admin/finance/period?jy={month['jy']}").json()
    assert year["kind"] == "year" and year["income"] == 400_000 and len(year["series"]) <= 12

    span = f"start={(today - timedelta(days=2)).isoformat()}&end={today.isoformat()}"
    custom = coach.get(f"/api/admin/finance/period?{span}").json()
    assert custom["kind"] == "range" and custom["income"] == 400_000 and custom["days"] == 3
    outside = coach.get(
        f"/api/admin/finance/period?start={(today - timedelta(days=30)).isoformat()}"
        f"&end={(today - timedelta(days=10)).isoformat()}").json()
    assert outside["income"] == 0 and outside["previous"]["income"] == 0

    backwards = f"start={today}&end={today - timedelta(days=1)}"
    assert coach.get(f"/api/admin/finance/period?{backwards}").status_code == 422
