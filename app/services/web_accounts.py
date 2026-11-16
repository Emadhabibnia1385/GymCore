"""Web panel accounts: a username and password, and signing up without Telegram.

Passwords are Argon2id hashes. A failed sign-in always says the same thing whether the
username exists or not, and costs the same time either way, so it reveals nothing.
Sign-ins and sign-ups are throttled per client, in memory (one API process).

A self-registered student gets a Person with no phone: the phone is the key that joins
a person across Telegram and Bale, and an unverified one typed on a web form would let
anyone claim someone else's account when that person later starts the bot. The coach
adds the phone, or the student links their Telegram from the panel.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict, deque

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AuthError, ConflictError, NotFoundError, ValidationError
from app.models import Person, Role, StudentType, WebCredential
from app.services import persons as persons_service

_hasher = PasswordHasher()
# Verified against when a username doesn't exist, so a miss takes as long as a hit.
_DUMMY_HASH = _hasher.hash("not-a-real-password")

_USERNAME = re.compile(r"^[a-z0-9][a-z0-9_.]{2,31}$")
PASSWORD_MIN, PASSWORD_MAX = 8, 128

BAD_LOGIN = "نام کاربری یا گذرواژه درست نیست"
TAKEN = "این نام کاربری قبلاً گرفته شده"
THROTTLED = "تلاش‌های زیادی شد؛ چند دقیقه صبر کن و دوباره امتحان کن"


class Throttled(AuthError):
    """Too many attempts from one client."""


class _Window:
    """At most `limit` events per `seconds`, per key."""

    def __init__(self, limit: int, seconds: int):
        self.limit, self.seconds = limit, seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def _trim(self, key: str, now: float) -> deque[float]:
        events = self._events[key]
        while events and now - events[0] > self.seconds:
            events.popleft()
        return events

    def blocked(self, key: str) -> bool:
        return len(self._trim(key, time.monotonic())) >= self.limit

    def hit(self, key: str) -> None:
        now = time.monotonic()
        self._trim(key, now).append(now)

    def clear(self, key: str) -> None:
        self._events.pop(key, None)

    def reset(self) -> None:
        self._events.clear()


failed_logins = _Window(limit=5, seconds=15 * 60)
signups = _Window(limit=5, seconds=60 * 60)


def normalize_username(raw: str) -> str:
    return (raw or "").strip().lower()


def check_username(username: str) -> str:
    if not _USERNAME.match(username):
        raise ValidationError(
            "نام کاربری ۳ تا ۳۲ نویسه باشد و فقط حروف انگلیسی، عدد، نقطه و زیرخط داشته باشد"
        )
    return username


def check_password(password: str, username: str = "") -> str:
    if not PASSWORD_MIN <= len(password or "") <= PASSWORD_MAX:
        raise ValidationError(f"گذرواژه حداقل {PASSWORD_MIN} نویسه باشد")
    if username and password.lower() == username.lower():
        raise ValidationError("گذرواژه نباید با نام کاربری یکی باشد")
    return password


def _taken(db: Session, username: str, except_person: int | None = None) -> bool:
    found = db.scalar(select(WebCredential).where(WebCredential.username == username))
    return found is not None and found.person_id != except_person


def register(db: Session, name: str, username: str, password: str, client: str = "") -> Person:
    """Open a student's account from the web form (client: the caller's address, for throttling)."""
    if client and signups.blocked(client):
        raise Throttled(THROTTLED)
    username = check_username(normalize_username(username))
    check_password(password, username)
    if _taken(db, username):
        raise ConflictError(TAKEN)
    person = persons_service.create(
        db, name=name, role=Role.CLIENT, student_type=StudentType.IN_PERSON
    )
    db.add(
        WebCredential(
            person_id=person.id, username=username, password_hash=_hasher.hash(password)
        )
    )
    db.commit()
    if client:
        signups.hit(client)
    return person


def authenticate(db: Session, username: str, password: str, client: str = "") -> Person:
    """The person for a username and password, or one generic AuthError."""
    key = f"{client}|{normalize_username(username)}"
    if failed_logins.blocked(key):
        raise Throttled(THROTTLED)
    credential = db.scalar(
        select(WebCredential).where(WebCredential.username == normalize_username(username))
    )
    stored = credential.password_hash if credential else _DUMMY_HASH
    try:
        _hasher.verify(stored, password or "")
        verified = credential is not None
    except (VerificationError, InvalidHashError):
        verified = False
    if not verified:
        failed_logins.hit(key)
        raise AuthError(BAD_LOGIN)
    person = db.get(Person, credential.person_id)
    if person is None or not person.is_active:
        failed_logins.hit(key)
        raise AuthError(BAD_LOGIN)
    failed_logins.clear(key)
    if _hasher.check_needs_rehash(credential.password_hash):
        credential.password_hash = _hasher.hash(password)
        db.commit()
    return person


def set_credentials(db: Session, person_id: int, username: str, password: str) -> WebCredential:
    """Create or replace a person's login (the coach gives a student access, or resets it)."""
    person = db.get(Person, person_id)
    if person is None:
        raise NotFoundError("شخص پیدا نشد")
    username = check_username(normalize_username(username))
    check_password(password, username)
    if _taken(db, username, except_person=person_id):
        raise ConflictError(TAKEN)
    credential = db.scalar(select(WebCredential).where(WebCredential.person_id == person_id))
    if credential is None:
        credential = WebCredential(person_id=person_id, username=username, password_hash="")
        db.add(credential)
    credential.username = username
    credential.password_hash = _hasher.hash(password)
    db.commit()
    return credential


def change_password(db: Session, person_id: int, old: str, new: str) -> None:
    credential = db.scalar(select(WebCredential).where(WebCredential.person_id == person_id))
    if credential is None:
        raise ValidationError("برای این حساب گذرواژه‌ای تعریف نشده")
    try:
        _hasher.verify(credential.password_hash, old or "")
    except (VerificationError, InvalidHashError):
        raise AuthError("گذرواژهٔ فعلی درست نیست") from None
    credential.password_hash = _hasher.hash(check_password(new, credential.username))
    db.commit()


def username_of(db: Session, person_id: int) -> str | None:
    return db.scalar(select(WebCredential.username).where(WebCredential.person_id == person_id))
