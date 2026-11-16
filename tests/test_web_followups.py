"""Timetable, follow-ups, leads, notes, settings, contacts and broadcast on the web."""
# ruff: noqa: E501  (request bodies read best on one line)

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.core import clock
from app.core.config import get_settings
from app.models import Platform
from app.services import auth as auth_service
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import crm as crm_service
from app.services import identities as identities_service
from app.services import notifications, web_auth
from app.services import persons as persons_service


@pytest.fixture()
def coach(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "web_cookie_secure", False)
    api = TestClient(app)
    person = identities_service.get_or_create_person(db, Platform.TELEGRAM, "111", "مربی")
    auth_service.sync_owner_role(db, Platform.TELEGRAM, "111", person)
    api.cookies.set("gc_session", web_auth.start_session(db, person, "111"))
    return api


def test_students_cannot_reach_follow_ups_settings_or_broadcast(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "web_cookie_secure", False)
    student = persons_service.create(db, name="سارا")
    identities_service.link_identity(db, student.id, Platform.TELEGRAM, "5001")
    api = TestClient(app)
    api.cookies.set("gc_session", web_auth.start_session(db, student, "5001"))
    for path in ("/api/admin/timetable", "/api/admin/followups/due", "/api/admin/renewals", "/api/admin/leads", "/api/admin/settings", "/api/admin/contacts", "/api/admin/notify/audience"):
        assert api.get(path).status_code == 403, path
    assert api.post("/api/admin/notify/broadcast", json={"text": "x"}).status_code == 403
    assert api.put("/api/admin/settings/card_number", json={"value": "1"}).status_code == 403


def test_the_weekly_timetable_lists_each_day_in_time_order(db, coach):
    student = persons_service.create(db, name="سارا")
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    courses_service.create(db, client_id=student.id, class_type_id=class_type.id, sessions_total=12, start_date=clock.today(), weekdays="0,2", class_times="0@18:00,2@09:30")
    week = coach.get("/api/admin/timetable").json()
    assert [d["name"] for d in week][:3] == ["شنبه", "یک‌شنبه", "دوشنبه"] and len(week) == 7
    assert week[0]["entries"][0]["time"] == "18:00" and week[2]["entries"][0]["time"] == "09:30"
    assert week[1]["entries"] == []


def test_follow_ups_are_listed_completed_and_postponed(db, coach):
    student = persons_service.create(db, name="سارا")
    crm_service.add_follow_up(db, clock.today(), person_id=student.id, note="تماس بگیر")
    assert coach.get("/api/admin/followups/summary").json()["due"] == 1
    (row,) = coach.get("/api/admin/followups/due").json()
    assert row["target"] == "سارا" and row["note"] == "تماس بگیر"
    assert coach.post(f"/api/admin/followups/{row['id']}/postpone", json={"days": 3}).status_code == 200
    assert coach.get("/api/admin/followups/due").json() == []  # now three days ahead
    assert coach.post(f"/api/admin/followups/{row['id']}/postpone", json={"days": 0}).status_code == 422
    made = coach.post("/api/admin/followups", json={"due_on": clock.today().isoformat(), "person_id": student.id, "note": "پیگیری جدید"})
    assert made.status_code == 200
    (fresh,) = coach.get("/api/admin/followups/due").json()
    assert coach.post(f"/api/admin/followups/{fresh['id']}/done").status_code == 200
    assert coach.get("/api/admin/followups/due").json() == []
    past = coach.post("/api/admin/followups", json={"due_on": (clock.today() - timedelta(days=2)).isoformat(), "person_id": student.id})
    assert past.status_code == 422  # a follow-up is due today or later


def test_a_lead_goes_from_new_to_a_student(db, coach):
    lead = coach.post("/api/admin/leads", json={"name": "علی رستمی", "phone": "09125556666", "source": "INSTAGRAM", "interest": "فیتنس"}).json()
    assert lead["status"] == "NEW" and lead["source_label"] == "اینستاگرام"
    contacted = coach.patch(f"/api/admin/leads/{lead['id']}", json={"status": "CONTACTED", "note": "زنگ زدم", "follow_up_on": (clock.today() + timedelta(days=2)).isoformat()}).json()
    assert contacted["status"] == "CONTACTED" and contacted["next_follow_up"] and "زنگ زدم" in contacted["note"]
    listed = coach.get("/api/admin/leads").json()
    assert listed["counts"]["CONTACTED"] == 1 and listed["rows"][0]["name"] == "علی رستمی"
    assert coach.get("/api/admin/leads?status=LOST").json()["rows"] == []
    done = coach.post(f"/api/admin/leads/{lead['id']}/convert", json={"kind": "ONLINE"}).json()
    assert done["linked"] is False
    profile = coach.get(f"/api/admin/students/{done['person_id']}").json()
    assert profile["name"] == "علی رستمی" and profile["kind"] == "ONLINE"
    assert coach.get("/api/admin/leads/options").json()["sources"][0]["value"]


def test_a_lead_whose_phone_is_already_a_student_is_linked_not_duplicated(db, coach):
    persons_service.create(db, name="مریم", phone="09121112222")
    lead = coach.post("/api/admin/leads", json={"name": "مریم تازه", "phone": "09121112222"}).json()
    assert lead["existing_student"] is not None
    done = coach.post(f"/api/admin/leads/{lead['id']}/convert", json={}).json()
    assert done["linked"] is True and done["person_id"] == lead["existing_student"]
    assert coach.post("/api/admin/leads", json={"name": ""}).status_code == 422
    assert coach.delete(f"/api/admin/leads/{lead['id']}").status_code == 200


def test_notes_form_an_append_only_timeline(db, coach):
    student = persons_service.create(db, name="سارا")
    assert coach.post(f"/api/admin/students/{student.id}/notes", json={"text": "گفت ماه بعد می‌آید"}).status_code == 200
    assert [n["text"] for n in coach.get(f"/api/admin/students/{student.id}/notes").json()] == ["گفت ماه بعد می‌آید"]
    assert coach.post(f"/api/admin/students/{student.id}/notes", json={"text": ""}).status_code == 422
    assert coach.get("/api/admin/students/999999/notes").status_code == 404


def test_settings_keep_their_validation(db, coach):
    rows = {r["key"]: r for r in coach.get("/api/admin/settings").json()}
    assert rows["notify_on_attendance"]["kind"] == "toggle" and rows["signup_url"]["kind"] == "link"
    assert rows["course_end_message"]["kind"] == "long" and rows["low_session_threshold"]["kind"] == "number"
    assert coach.put("/api/admin/settings/low_session_threshold", json={"value": "دو"}).status_code == 422
    assert coach.put("/api/admin/settings/signup_url", json={"value": "mahdisarmad.ir"}).status_code == 422
    assert coach.put("/api/admin/settings/card_number", json={"value": ""}).status_code == 422
    assert coach.put("/api/admin/settings/nope", json={"value": "x"}).status_code == 422
    assert coach.put("/api/admin/settings/low_session_threshold", json={"value": "3"}).status_code == 200
    assert coach.put("/api/admin/settings/notify_on_attendance", json={"value": "0"}).status_code == 200
    now = {r["key"]: r["value"] for r in coach.get("/api/admin/settings").json()}
    assert (now["low_session_threshold"], now["notify_on_attendance"]) == ("3", "0")


def test_contact_links_are_edited_toggled_and_reordered(db, coach):
    links = coach.get("/api/admin/contacts").json()
    first, second = links[0], links[1]
    out = coach.patch(f"/api/admin/contacts/{first['id']}", json={"label": "تلفن مربی", "active": False}).json()
    assert out["label"] == "تلفن مربی" and out["active"] is False
    assert coach.post(f"/api/admin/contacts/{second['id']}/move", json={"direction": -1}).status_code == 200
    assert coach.get("/api/admin/contacts").json()[0]["id"] == second["id"]


def test_a_broadcast_reaches_students_the_bot_can_message(db, coach, monkeypatch):
    sent = []
    monkeypatch.setattr(notifications, "enabled", True)
    monkeypatch.setattr("app.notifications.service._default_sender", lambda platform, chat_id, text: sent.append((chat_id, text)) or True)
    student = persons_service.create(db, name="سارا")
    identities_service.link_identity(db, student.id, Platform.TELEGRAM, "5001")
    persons_service.create(db, name="بدون ربات")  # can't be reached
    assert coach.get("/api/admin/notify/audience").json() == {"count": 1}
    res = coach.post("/api/admin/notify/broadcast", json={"text": "سلام به همه"})
    assert res.status_code == 200 and res.json()["count"] == 1
    assert coach.post("/api/admin/notify/broadcast", json={"text": ""}).status_code == 422
    assert coach.post("/api/admin/notify/low-sessions").status_code == 200
