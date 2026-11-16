"""Connect a Telegram account to a username/password web account.

The web account (W) was made with a password and has no Telegram; the Telegram account's
person (P) was made by the bot on first contact. Joining them means one person holds both
the password and the Telegram identity, so sign-in works either way.

Which person survives is decided by what each holds:
- W empty (just registered): the password moves to P, and W goes.
- P empty (a new Telegram user who shared a phone, nothing else): the Telegram identity and
  phone move to W, and P goes.
- both hold data, or P is staff, or P already has a web account: refused. Merging two
  histories is the coach's call, not a button's.

The person pressing «تأیید» in Telegram is the only authority; the bot names the account.
"""

from __future__ import annotations

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models import (
    ChannelIdentity,
    Course,
    FollowUp,
    Lead,
    Notification,
    PackageAssignment,
    Payment,
    Person,
    PersonNote,
    PlanAssignment,
    Platform,
    Role,
    WebCredential,
    WebSession,
)

LINKED, ALREADY, REFUSED_STAFF, REFUSED_HAS_WEB, REFUSED_BOTH = (
    "linked", "already", "staff", "has_web", "both",
)

# What makes a person "someone", beyond a name, a phone and a Telegram id.
_HISTORY = (
    (Course, Course.client_id), (Payment, Payment.person_id),
    (PlanAssignment, PlanAssignment.person_id), (PackageAssignment, PackageAssignment.person_id),
    (Lead, Lead.person_id), (PersonNote, PersonNote.person_id),
)


def has_telegram(db: Session, person_id: int) -> bool:
    return db.scalar(select(func.count()).select_from(ChannelIdentity).where(
        ChannelIdentity.person_id == person_id, ChannelIdentity.platform == Platform.TELEGRAM,
    )) > 0


def _has_history(db: Session, person_id: int) -> bool:
    return any(
        db.scalar(select(func.count()).select_from(model).where(column == person_id))
        for model, column in _HISTORY
    )


def _forget(db: Session, person_id: int) -> None:
    """Remove an empty person: only the traces a person with no history can have."""
    db.execute(delete(FollowUp).where(FollowUp.person_id == person_id))
    db.execute(delete(Notification).where(Notification.person_id == person_id))
    db.execute(delete(ChannelIdentity).where(ChannelIdentity.person_id == person_id))
    db.execute(delete(WebSession).where(WebSession.person_id == person_id))
    db.execute(delete(Person).where(Person.id == person_id))


def link(db: Session, web_person_id: int, telegram_person: Person, telegram_user_id: str) -> str:
    """Join the two; returns one of the outcome codes above."""
    web = db.get(Person, web_person_id)
    if web is None or not web.is_active:
        return REFUSED_BOTH
    if telegram_person.id == web.id:
        return ALREADY
    if telegram_person.role != Role.CLIENT:
        return REFUSED_STAFF
    if db.scalar(select(WebCredential).where(WebCredential.person_id == telegram_person.id)):
        return REFUSED_HAS_WEB

    if web.role == Role.CLIENT and not _has_history(db, web.id):
        # The fresh web account gives its password to the Telegram person and goes.
        credential = db.scalar(select(WebCredential).where(WebCredential.person_id == web.id))
        if credential is not None:
            credential.person_id = telegram_person.id
        db.execute(
            update(WebSession).where(WebSession.person_id == web.id).values(
                person_id=telegram_person.id, telegram_user_id=str(telegram_user_id)
            )
        )
        db.execute(
            update(FollowUp)
            .where(FollowUp.person_id == web.id)
            .values(person_id=telegram_person.id)
        )
        db.flush()
        _forget(db, web.id)
        db.commit()
        return LINKED

    if not _has_history(db, telegram_person.id):
        # A newcomer on Telegram joins the web account that already has a story.
        if telegram_person.phone and not web.phone:
            phone, telegram_person.phone = telegram_person.phone, None
            db.flush()
            web.phone = phone
        db.execute(
            update(ChannelIdentity)
            .where(ChannelIdentity.person_id == telegram_person.id)
            .values(person_id=web.id)
        )
        db.execute(
            update(WebSession).where(WebSession.person_id == web.id).values(
                telegram_user_id=str(telegram_user_id)
            )
        )
        db.flush()
        _forget(db, telegram_person.id)
        db.commit()
        return LINKED
    return REFUSED_BOTH
