"""Web panel sign-in: verify «Login with Telegram», then keep the browser signed in.

Telegram signs the widget's payload with a key derived from the bot token, so a
valid `hash` proves the account is who it says — no password anywhere. A
signed-in browser holds a random token in a cookie; only its SHA-256 is stored.
A session lives for `SESSION_DAYS` of disuse and slides forward whenever it is
used, so a student who opens the panel now and then never signs in twice.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core import admin_auth
from app.core.exceptions import AuthError
from app.models import Person, Platform, Role, WebSession
from app.services import auth as auth_service
from app.services import identities as identities_service

SESSION_DAYS = 180
# Slide the expiry at most this often, so reads don't write on every request.
_SLIDE_EVERY = timedelta(hours=12)
# A Telegram signature older than this is a replay, not a login.
_MAX_AUTH_AGE = timedelta(hours=24)

# Fields Telegram's widget sends; anything else in the payload is ignored.
_WIDGET_FIELDS = ("id", "first_name", "last_name", "username", "photo_url", "auth_date")

NOT_ALLOWED = (
    "این حساب تلگرام هنوز در GymCore ثبت نشده؛ "
    "اول ربات را استارت کن و بعد دوباره وارد شو."
)


def _now() -> datetime:
    return datetime.now(UTC)


def verify_telegram_login(payload: dict, bot_token: str, now: datetime | None = None) -> dict:
    """The widget's fields when the signature is genuine and fresh, else AuthError."""
    received = str(payload.get("hash") or "")
    if not bot_token or not received:
        raise AuthError("ورود با تلگرام در دسترس نیست")
    fields = {k: str(payload[k]) for k in _WIDGET_FIELDS if payload.get(k) not in (None, "")}
    check = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    key = hashlib.sha256(bot_token.encode()).digest()
    expected = hmac.new(key, check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received):
        raise AuthError("امضای ورود تلگرام معتبر نیست")
    try:
        signed_at = datetime.fromtimestamp(int(fields["auth_date"]), UTC)
    except (KeyError, ValueError, OverflowError):
        raise AuthError("امضای ورود تلگرام معتبر نیست") from None
    if (now or _now()) - signed_at > _MAX_AUTH_AGE:
        raise AuthError("ورود منقضی شده؛ دوباره امتحان کن")
    if "id" not in fields or not fields["id"].isdigit():
        raise AuthError("امضای ورود تلگرام معتبر نیست")
    return fields


def person_for_login(db: Session, fields: dict) -> Person:
    """The Person behind a verified Telegram account.

    A configured owner gets a Person on first sign-in; everyone else must
    already be known to the bot, so a stranger can't create records by logging in.
    """
    user_id = fields["id"]
    name = " ".join(p for p in (fields.get("first_name"), fields.get("last_name")) if p)
    if admin_auth.is_owner(Platform.TELEGRAM, user_id):
        person = identities_service.get_or_create_person(
            db, Platform.TELEGRAM, user_id, name, fields.get("username")
        )
        auth_service.sync_owner_role(db, Platform.TELEGRAM, user_id, person)
        return person
    person = identities_service.find_person(db, Platform.TELEGRAM, user_id)
    if person is None or not person.is_active:
        raise AuthError(NOT_ALLOWED)
    return person


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(
    db: Session, person: Person, telegram_user_id: str | None, user_agent: str | None = None
) -> str:
    """Open a session and return the cookie token (shown once, never stored)."""
    token = secrets.token_urlsafe(32)
    now = _now()
    db.add(WebSession(
        person_id=person.id,
        telegram_user_id=telegram_user_id,
        token_hash=_hash(token),
        user_agent=(user_agent or "")[:200] or None,
        expires_at=now + timedelta(days=SESSION_DAYS),
    ))
    # Tidy lapsed sessions as they would otherwise pile up.
    db.execute(delete(WebSession).where(WebSession.expires_at < now))
    db.commit()
    return token


def resolve_session(db: Session, token: str | None) -> WebSession | None:
    """The live session for a cookie token, slid forward; None if unknown or lapsed."""
    if not token:
        return None
    session = db.scalar(select(WebSession).where(WebSession.token_hash == _hash(token)))
    now = _now()
    if session is None or _aware(session.expires_at) < now:
        return None
    if now - _aware(session.last_seen_at) > _SLIDE_EVERY:
        session.last_seen_at = now
        session.expires_at = now + timedelta(days=SESSION_DAYS)
        db.commit()
    return session


def end_session(db: Session, token: str | None) -> None:
    if token:
        db.execute(delete(WebSession).where(WebSession.token_hash == _hash(token)))
        db.commit()


def is_admin(db: Session, person_id: int, telegram_user_id: str | None) -> bool:
    """Coach rights for a signed-in person.

    A Telegram sign-in is the bot's own check (owner whitelist or a COACH/ADMIN role).
    A password sign-in has no Telegram id, so it relies on that role — which only a
    configured owner ever holds, so a student can never be promoted by registering.
    """
    if telegram_user_id:
        return auth_service.is_admin(db, Platform.TELEGRAM, telegram_user_id)
    person = db.get(Person, person_id)
    return person is not None and person.role in (Role.COACH, Role.ADMIN)


def _aware(moment: datetime) -> datetime:
    # SQLite hands timestamps back naive (they are stored as UTC).
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)
