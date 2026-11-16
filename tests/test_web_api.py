"""The web panel's sign-in and dashboards, through the real FastAPI app."""

import hashlib
import hmac
import time
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.core import clock
from app.core.config import get_settings
from app.models import Platform, WebSession
from app.services import identities as identities_service
from app.services import persons as persons_service

BOT_TOKEN = "123456:TEST-TOKEN"
OWNER = "111"  # a configured Telegram owner (tests/conftest.py)


@pytest.fixture(autouse=True)
def _bot_token(monkeypatch):
    monkeypatch.setattr(get_settings(), "telegram_bot_token", BOT_TOKEN)
    monkeypatch.setattr(get_settings(), "web_cookie_secure", False)


@pytest.fixture()
def client(db):
    return TestClient(app)


def _signed(user_id, first_name="کاربر", auth_date=None, token=BOT_TOKEN, **extra):
    fields = {"id": str(user_id), "first_name": first_name,
              "auth_date": str(auth_date or int(time.time())), **extra}
    check = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    key = hashlib.sha256(token.encode()).digest()
    fields["hash"] = hmac.new(key, check.encode(), hashlib.sha256).hexdigest()
    return fields


def test_the_login_button_knows_the_bot(client):
    assert client.get("/api/auth/config").json() == {"bot_username": "MahdiSarmad_BOT"}


def test_a_forged_or_stale_signature_is_refused(client):
    tampered = _signed(OWNER)
    tampered["first_name"] = "کس دیگر"
    assert client.post("/api/auth/telegram", json=tampered).status_code == 403
    wrong_key = _signed(OWNER, token="999:OTHER")
    assert client.post("/api/auth/telegram", json=wrong_key).status_code == 403
    stale = _signed(OWNER, auth_date=int(time.time()) - 2 * 86400)
    assert client.post("/api/auth/telegram", json=stale).status_code == 403
    assert client.get("/api/auth/me").status_code == 401


def test_the_coach_signs_in_and_stays_signed_in(db, client):
    res = client.post("/api/auth/telegram", json=_signed(OWNER, "مهدی"))
    assert res.status_code == 200 and res.json() == {"name": "مهدی", "role": "admin"}
    cookie = res.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie
    # The cookie alone keeps him in — no second login.
    assert client.get("/api/auth/me").json()["role"] == "admin"
    # The raw token is never stored, only its hash.
    row = db.query(WebSession).one()
    assert row.token_hash not in cookie


def test_a_known_student_is_a_student_and_not_an_admin(db, client):
    student = persons_service.create(db, name="سارا")
    identities_service.link_identity(db, student.id, Platform.TELEGRAM, "5001")
    res = client.post("/api/auth/telegram", json=_signed(5001, "سارا"))
    assert res.json() == {"name": "سارا", "role": "student"}
    assert client.get("/api/admin/dashboard").status_code == 403


def test_a_stranger_cannot_make_an_account_by_logging_in(db, client):
    res = client.post("/api/auth/telegram", json=_signed(777777))
    assert res.status_code == 403
    assert identities_service.find_person(db, Platform.TELEGRAM, "777777") is None


def test_logout_ends_the_session(db, client):
    client.post("/api/auth/telegram", json=_signed(OWNER))
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401
    assert db.query(WebSession).count() == 0


def test_an_unused_session_lapses_but_a_used_one_slides(db, client):
    client.post("/api/auth/telegram", json=_signed(OWNER))
    row = db.query(WebSession).one()
    row.last_seen_at = datetime.now(UTC) - timedelta(days=2)
    row.expires_at = datetime.now(UTC) + timedelta(days=10)
    db.commit()
    assert client.get("/api/auth/me").status_code == 200  # opening it slides it forward
    db.expire_all()
    slid = db.query(WebSession).one().expires_at.replace(tzinfo=UTC)  # SQLite returns naive UTC
    assert slid > datetime.now(UTC) + timedelta(days=170)
    db.query(WebSession).one().expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()
    assert client.get("/api/auth/me").status_code == 401


def test_the_admin_dashboard_reports_the_gyms_real_numbers(db, client):
    from app.models import ExpenseCategory, PaymentKind
    from app.services import classes as classes_service
    from app.services import courses as courses_service
    from app.services import finance as finance_service
    from app.services import payments as payments_service

    student = persons_service.create(db, name="سارا")
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=student.id, class_type_id=class_type.id, sessions_total=12,
        tuition=1_000_000, start_date=clock.today(), weekdays="0,1,2,3,4,5,6",
        class_times="0@18:00,1@18:00,2@18:00,3@18:00,4@18:00,5@18:00,6@18:00",
    )
    payments_service.record(db, student.id, 400_000, PaymentKind.TUITION, clock.today(),
                            course_id=course.id, notify=False)
    finance_service.record_expense(db, 150_000, ExpenseCategory.BILLS, clock.today())
    client.post("/api/auth/telegram", json=_signed(OWNER))
    data = client.get("/api/admin/dashboard").json()
    assert data["month"]["income"] == 400_000 and data["month"]["expenses"] == 150_000
    assert data["month"]["net"] == 250_000
    assert data["owing"] == {"count": 1, "total": 600_000, "top": [
        {"student": "سارا", "class_title": class_type.title, "amount": 600_000}]}
    assert data["today"] == [{"time": "18:00", "student": "سارا", "class_title": class_type.title}]
    assert len(data["months"]) == 12 and data["totals"]["active_courses"] == 1
