"""Tracked notification system: queue → deliver (retry) → dispatch scheduled.

This is the durable, de-duplicated, retryable path used for broadcasts,
scheduled messages and automatic reminders (low sessions, course ending). Each
Notification carries its own lifecycle (scheduledFor / sentAt / failedAt /
retryCount / lastError) and an optional idempotency key so nothing is delivered
twice.

Real-time confirmations (attendance recorded, payment received, new program
delivered) use the fire-and-forget path in `app.services.notifications`; this
module is the async ledger.

Timestamps are stored as naive-UTC for consistent comparison on SQLite and
PostgreSQL.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.bots.common.client import build_client
from app.models import (
    CourseStatus,
    Notification,
    NotificationKind,
    NotificationStatus,
    Person,
    Platform,
    Role,
)
from app.models.setting import KEY_LOW_SESSION_THRESHOLD
from app.services import courses as courses_service
from app.services import settings as settings_service

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
_BOT_PLATFORMS = (Platform.TELEGRAM, Platform.BALE)


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _default_sender(platform: Platform, chat_id: str, text: str) -> bool:
    client = build_client(platform)
    if client is None:
        return False
    try:
        client.send_message(chat_id, text)
        return True
    except Exception:
        logger.warning("notification send failed on %s", platform.value)
        return False
    finally:
        client.close()


# Tests override this to stay offline / deterministic.
sender = _default_sender


def queue(
    db: Session,
    person_id: int | None,
    kind: NotificationKind,
    body: str,
    title: str | None = None,
    scheduled_for: datetime | None = None,
    idempotency_key: str | None = None,
    created_by: str | None = None,
) -> Notification | None:
    """Create a PENDING notification, or None if the idempotency key already exists."""
    if idempotency_key:
        existing = db.scalar(
            select(Notification).where(Notification.idempotency_key == idempotency_key)
        )
        if existing is not None:
            return None
    notification = Notification(
        person_id=person_id,
        kind=kind,
        title=title,
        body=body,
        status=NotificationStatus.PENDING,
        scheduled_for=scheduled_for,
        idempotency_key=idempotency_key,
        created_by=created_by,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def _targets(db: Session, person_id: int | None) -> list[tuple[Platform, str]]:
    if person_id is None:
        return []
    person = db.get(Person, person_id)
    if person is None:
        return []
    return [
        (identity.platform, identity.platform_user_id)
        for identity in person.identities
        if identity.platform in _BOT_PLATFORMS
    ]


def deliver(db: Session, notification: Notification, now: datetime | None = None) -> bool:
    """Attempt delivery once; update lifecycle fields. Idempotent on status."""
    if notification.status != NotificationStatus.PENDING:
        return False
    stamp = now or utcnow()
    targets = _targets(db, notification.person_id)
    if not targets:
        # Nothing to deliver to — mark sent (no-op) so it never retries forever.
        notification.status = NotificationStatus.SENT
        notification.sent_at = stamp
        db.commit()
        return False

    delivered = any(sender(platform, chat_id, notification.body) for platform, chat_id in targets)
    if delivered:
        notification.status = NotificationStatus.SENT
        notification.sent_at = stamp
        notification.last_error = None
    else:
        notification.retry_count += 1
        notification.failed_at = stamp
        notification.last_error = "delivery failed"
        if notification.retry_count >= MAX_RETRIES:
            notification.status = NotificationStatus.FAILED
    db.commit()
    return delivered


def dispatch_due(db: Session, now: datetime | None = None) -> int:
    """Deliver every PENDING notification that is due (not scheduled in the future)."""
    stamp = now or utcnow()
    stmt = (
        select(Notification)
        .where(
            Notification.status == NotificationStatus.PENDING,
            or_(Notification.scheduled_for.is_(None), Notification.scheduled_for <= stamp),
        )
        .order_by(Notification.id)
    )
    delivered = 0
    for notification in db.scalars(stmt).all():
        if deliver(db, notification, now=stamp):
            delivered += 1
    return delivered


def broadcast(db: Session, body: str, created_by: str | None = None) -> int:
    """Queue a BROADCAST notification for every active client with a bot account."""
    clients = db.scalars(
        select(Person).where(Person.role == Role.CLIENT, Person.is_active.is_(True))
    ).all()
    count = 0
    for client in clients:
        if any(identity.platform in _BOT_PLATFORMS for identity in client.identities):
            queue(db, client.id, NotificationKind.BROADCAST, body, created_by=created_by)
            count += 1
    return count


def generate_reminders(db: Session, now: datetime | None = None) -> int:
    """Queue low-session reminders for active courses (idempotent, never spammy).

    Course-ending notifications are queued event-driven when a course auto-finishes
    (see services.attendance), so old finished courses are never notified twice.
    """
    threshold = settings_service.get_int(db, KEY_LOW_SESSION_THRESHOLD, 2)
    queued = 0
    for course in courses_service.list_courses(db, status=CourseStatus.ACTIVE):
        remaining = courses_service.remaining_sessions(db, course)
        if 0 < remaining <= threshold:
            # Keyed by remaining count → one reminder per threshold step, no spam.
            key = f"low:{course.id}:{remaining}"
            body = (
                f"⚠️ فقط {remaining} جلسه از دورهٔ «{course.class_type.title}» باقی مانده است.\n"
                "برای تمدید با مربی هماهنگ کن 🟢"
            )
            created = queue(
                db, course.client_id, NotificationKind.LOW_SESSIONS, body, idempotency_key=key
            )
            if created is not None:
                queued += 1
    return queued
