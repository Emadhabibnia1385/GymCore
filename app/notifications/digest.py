"""The coach's morning summary of «📇 پیگیری‌ها».

Once a day — on the first worker run after 08:00 in the coach's timezone — the
owners get one line: follow-ups due, students who should renew, open leads.
Only when something is waiting for them (services/crm.py::summary): a
follow-up due, a finished course nobody has followed up on, or a new lead
nobody has contacted or scheduled. That first run decides for the whole day,
so a quiet morning stays quiet instead of a digest arriving mid-afternoon.

Owners are the numeric IDs in TELEGRAM_OWNER_IDS / BALE_OWNER_IDS. A bot can
only message someone who has opened it, which is exactly when an owner gets a
Person (client_flow._provision_owner), so the digest goes through the ordinary
notification ledger to those Persons: one row per owner per day, keyed
``crm-digest:<day>:<person_id>`` so it is never delivered twice. A quiet day
is recorded as a CANCELLED row (``crm-digest:<day>:quiet``) — the decision.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.copy import crm_texts as C
from app.core.admin_auth import owner_ids
from app.models import Notification, NotificationKind, NotificationStatus, Person, Platform
from app.notifications import service
from app.services import crm as crm_service
from app.services import identities as identities_service

DIGEST_HOUR = 8  # in the coach's timezone (settings.timezone)
_CREATED_BY = "crm-digest"


def _key(day: str, target: object) -> str:
    return f"crm-digest:{day}:{target}"


def owner_persons(db: Session) -> list[Person]:
    """The Persons behind the configured owner IDs — owners who have opened a bot."""
    found: dict[int, Person] = {}
    for platform in (Platform.TELEGRAM, Platform.BALE):
        for owner_id in owner_ids(platform):
            person = identities_service.find_person(db, platform, str(owner_id))
            if person is not None:
                found.setdefault(person.id, person)
    return list(found.values())


def queue_digest(db: Session, now: datetime | None = None) -> int:
    """Queue today's digest for the owners; returns how many were queued.

    `now` is naive UTC (the ledger's convention) or aware; defaults to now.
    """
    local = crm_service.local_now(now)
    if local.hour < DIGEST_HOUR:
        return 0
    day = local.date().isoformat()
    if _decided(db, day):
        return 0
    owners = owner_persons(db)
    if not owners:
        return 0  # nobody can be told yet; an owner opening the bot later today still is
    summary = crm_service.summary(db, local.date())
    body = C.DIGEST.format(due=summary.due, renewals=summary.renewals, leads=summary.leads)
    if not summary.waiting:
        db.add(Notification(
            person_id=None,
            kind=NotificationKind.MANUAL,
            body=body,
            status=NotificationStatus.CANCELLED,
            idempotency_key=_key(day, "quiet"),
            created_by=_CREATED_BY,
        ))
        db.commit()
        return 0
    queued = 0
    for person in owners:
        created = service.queue(
            db, person.id, NotificationKind.MANUAL, body,
            idempotency_key=_key(day, person.id), created_by=_CREATED_BY,
        )
        if created is not None:
            queued += 1
    return queued


def _decided(db: Session, day: str) -> bool:
    """Whether today's digest was already queued, or skipped as a quiet day."""
    prefix = _key(day, "")
    return db.scalar(
        select(Notification.id)
        .where(Notification.idempotency_key.startswith(prefix, autoescape=True))
        .limit(1)
    ) is not None
