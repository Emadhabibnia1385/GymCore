"""Tracked notification system: queue dedup, delivery lifecycle, retry,
scheduling, broadcast, reminders, and event-driven course-ending."""

from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models import (
    AttendanceStatus,
    Notification,
    NotificationKind,
    NotificationStatus,
    Platform,
    Role,
)
from app.notifications import service
from app.services import attendance as attendance_service
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import identities as identities_service
from app.services import persons as persons_service


@pytest.fixture
def sender():
    """Patch the notification sender with an offline recorder."""
    calls: list = []
    state = {"ok": True}

    def _send(platform, chat_id, text):
        calls.append((platform, chat_id, text))
        return state["ok"]

    original = service.sender
    service.sender = _send
    yield calls, state
    service.sender = original


def _client_with_identity(db, uid="900", name="گیرنده"):
    return identities_service.get_or_create_person(db, Platform.TELEGRAM, uid, name)


def test_queue_idempotency_dedup(db):
    first = service.queue(db, None, NotificationKind.MANUAL, "x", idempotency_key="k1")
    second = service.queue(db, None, NotificationKind.MANUAL, "x", idempotency_key="k1")
    assert first is not None
    assert second is None
    assert len(db.scalars(select(Notification)).all()) == 1


def test_dispatch_delivers_and_marks_sent(db, sender):
    calls, _ = sender
    person = _client_with_identity(db)
    service.queue(db, person.id, NotificationKind.MANUAL, "سلام")
    assert service.dispatch_due(db) == 1
    assert len(calls) == 1
    notification = db.scalar(select(Notification))
    assert notification.status == NotificationStatus.SENT
    assert notification.sent_at is not None


def test_dispatch_retries_then_fails(db, sender):
    _, state = sender
    state["ok"] = False
    person = _client_with_identity(db)
    service.queue(db, person.id, NotificationKind.MANUAL, "x")
    for _ in range(service.MAX_RETRIES):
        service.dispatch_due(db)
    notification = db.scalar(select(Notification))
    assert notification.status == NotificationStatus.FAILED
    assert notification.retry_count == service.MAX_RETRIES
    assert notification.last_error


def test_scheduled_not_delivered_until_due(db, sender):
    person = _client_with_identity(db)
    now = service.utcnow()
    service.queue(
        db, person.id, NotificationKind.MANUAL, "later",
        scheduled_for=now + timedelta(hours=1),
    )
    assert service.dispatch_due(db, now=now) == 0
    assert db.scalar(select(Notification)).status == NotificationStatus.PENDING
    assert service.dispatch_due(db, now=now + timedelta(hours=2)) == 1
    assert db.scalar(select(Notification)).status == NotificationStatus.SENT


def test_no_targets_marked_sent_noop(db, sender):
    calls, _ = sender
    person = persons_service.create(db, name="بی‌حساب", role=Role.CLIENT)  # no identity
    service.queue(db, person.id, NotificationKind.MANUAL, "x")
    assert service.dispatch_due(db) == 0  # nothing actually sent
    assert not calls
    assert db.scalar(select(Notification)).status == NotificationStatus.SENT


def test_broadcast_only_clients_with_identity(db):
    with_id = _client_with_identity(db, "901", "با")
    persons_service.create(db, name="بدون", role=Role.CLIENT)  # no identity
    assert service.broadcast(db, "پیام همگانی") == 1
    notifications = db.scalars(select(Notification)).all()
    assert len(notifications) == 1
    assert notifications[0].person_id == with_id.id
    assert notifications[0].kind == NotificationKind.BROADCAST


def test_generate_low_session_reminders_idempotent(db):
    person = _client_with_identity(db, "902")
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=person.id, class_type_id=class_type.id, sessions_total=2
    )
    attendance_service.record(
        db, course.id, date(2026, 7, 1), AttendanceStatus.PRESENT, notify=False
    )
    assert service.generate_reminders(db) == 1
    assert service.generate_reminders(db) == 0  # dedup by (course, remaining)
    assert db.scalar(
        select(Notification).where(Notification.kind == NotificationKind.LOW_SESSIONS)
    ) is not None


def test_course_ending_queued_on_exhaustion(db):
    person = _client_with_identity(db, "903")
    class_type = classes_service.list_class_types(db, only_active=True)[0]
    course = courses_service.create(
        db, client_id=person.id, class_type_id=class_type.id, sessions_total=1
    )
    attendance_service.record(
        db, course.id, date(2026, 7, 1), AttendanceStatus.PRESENT, notify=False
    )
    ending = db.scalar(
        select(Notification).where(Notification.kind == NotificationKind.COURSE_ENDING)
    )
    assert ending is not None
    assert ending.idempotency_key == f"ending:{course.id}"
