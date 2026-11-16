"""Programs and packages from the web."""
# ruff: noqa: E501  (request bodies read best on one line)

import pytest
from fastapi.testclient import TestClient

from app.api.main import app
from app.core.config import get_settings
from app.models import Platform
from app.services import auth as auth_service
from app.services import identities as identities_service
from app.services import packages as packages_service
from app.services import persons as persons_service
from app.services import plans as plans_service
from app.services import web_auth


@pytest.fixture()
def coach(db, monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "web_cookie_secure", False)
    monkeypatch.setattr(get_settings(), "upload_dir", tmp_path)
    api = TestClient(app)
    person = identities_service.get_or_create_person(db, Platform.TELEGRAM, "111", "مربی")
    auth_service.sync_owner_role(db, Platform.TELEGRAM, "111", person)
    api.cookies.set("gc_session", web_auth.start_session(db, person, "111"))
    return api


def test_students_cannot_manage_programs_or_packages(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "web_cookie_secure", False)
    student = persons_service.create(db, name="سارا")
    identities_service.link_identity(db, student.id, Platform.TELEGRAM, "5001")
    api = TestClient(app)
    api.cookies.set("gc_session", web_auth.start_session(db, student, "5001"))
    for path in ("/api/admin/packages", "/api/admin/program-types"):
        assert api.get(path).status_code == 403
    assert api.post("/api/admin/programs", data={"person_id": student.id, "plan_type_id": 1, "note": "x"}).status_code == 403
    assert api.post("/api/admin/packages", json={"title": "x"}).status_code == 403


def test_program_types_are_managed_and_a_used_one_stays(db, coach):
    made = coach.post("/api/admin/program-types", json={"title": "برنامه تمرینی"}).json()["id"]
    coach.patch(f"/api/admin/program-types/{made}", json={"title": "تمرین", "active": False})
    assert next(t for t in coach.get("/api/admin/program-types").json() if t["id"] == made) == {"id": made, "title": "تمرین", "active": False}
    student = persons_service.create(db, name="سارا")
    plans_service.create_assignment(db, person_id=student.id, plan_type_id=made, coach_note="x", notify=False)
    assert coach.delete(f"/api/admin/program-types/{made}").status_code == 422  # in use: deactivate instead


def test_a_program_is_sent_with_a_note_and_a_file_but_never_empty(db, coach):
    student = persons_service.create(db, name="سارا")
    kind = coach.post("/api/admin/program-types", json={"title": "تغذیه"}).json()["id"]
    form = {"person_id": student.id, "plan_type_id": kind}
    assert coach.post("/api/admin/programs", data=form).status_code == 422  # neither file nor text
    text = coach.post("/api/admin/programs", data={**form, "note": "صبحانه: جو دوسر"})
    assert text.status_code == 200
    pdf = coach.post("/api/admin/programs", data={**form, "note": "هفته اول"}, files={"file": ("diet.pdf", b"%PDF-1.4 test", "application/pdf")})
    assert pdf.status_code == 200
    rows = {a.id: a for a in plans_service.list_assignments(db, person_id=student.id)}
    assert rows[pdf.json()["id"]].original_filename == "diet.pdf" and plans_service.attachment_path(rows[pdf.json()["id"]]) is not None
    bad = coach.post("/api/admin/programs", data=form, files={"file": ("run.exe", b"MZ", "application/octet-stream")})
    assert bad.status_code == 422
    assert coach.post("/api/admin/programs", data={**form, "person_id": 99999, "note": "x"}).status_code == 404


def test_a_package_is_built_ordered_sent_and_revoked(db, coach):
    made = coach.post("/api/admin/packages", json={"title": "پکیج کاهش وزن", "description": "هشت هفته"}).json()["id"]
    assert coach.post(f"/api/admin/packages/{made}/items", json={"text": ""}).status_code == 422
    first = coach.post(f"/api/admin/packages/{made}/items", json={"title": "هفته ۱", "text": "آب بنوش"}).json()
    detail = coach.post(f"/api/admin/packages/{made}/items", json={"text": "پیاده‌روی"}).json()
    ids = [i["id"] for i in detail["item_list"]]
    assert [i["kind"] for i in detail["item_list"]] == ["text", "text"] and len(ids) == 2 and first["items"] == 1
    moved = coach.post(f"/api/admin/package-items/{ids[1]}/move", json={"direction": -1}).json()
    assert [i["id"] for i in moved["item_list"]] == [ids[1], ids[0]]
    edited = coach.patch(f"/api/admin/package-items/{ids[0]}", json={"text": "آب بنوش ۸ لیوان"}).json()
    assert any(i["text"] == "آب بنوش ۸ لیوان" for i in edited["item_list"])

    a, b = persons_service.create(db, name="سارا"), persons_service.create(db, name="مریم")
    sent = coach.post(f"/api/admin/packages/{made}/assign", json={"person_ids": [a.id, b.id]}).json()
    assert sent["count"] == 2
    assert coach.post(f"/api/admin/packages/{made}/assign", json={"person_ids": [a.id]}).json()["count"] == 0  # idempotent
    listed = coach.get("/api/admin/packages").json()[0]
    assert (listed["items"], listed["recipients"]) == (2, 2)
    detail = coach.get(f"/api/admin/packages/{made}").json()
    assert detail["ever_assigned"] is True
    assert coach.delete(f"/api/admin/packages/{made}").status_code == 422  # ever sent: deactivate instead
    revoked = coach.post(f"/api/admin/package-assignments/{detail['recipient_list'][0]['assignment_id']}/revoke")
    assert revoked.status_code == 200
    assert coach.get(f"/api/admin/packages/{made}").json()["recipients"] == 1
    assert coach.patch(f"/api/admin/packages/{made}", json={"active": False}).json()["active"] is False
    assert coach.post(f"/api/admin/packages/{made}/assign", json={"person_ids": [a.id]}).status_code == 422  # inactive


def test_an_empty_package_cannot_be_sent_and_a_stranger_is_refused(db, coach):
    made = coach.post("/api/admin/packages", json={"title": "خالی"}).json()["id"]
    student = persons_service.create(db, name="سارا")
    assert coach.post(f"/api/admin/packages/{made}/assign", json={"person_ids": [student.id]}).status_code == 422
    packages_service.add_item(db, made, kind="text", text="x")
    assert coach.post(f"/api/admin/packages/{made}/assign", json={"person_ids": [99999]}).status_code == 404
    assert coach.get("/api/admin/packages/99999").status_code == 404
    assert coach.patch("/api/admin/package-items/99999", json={"text": "x"}).status_code == 404
