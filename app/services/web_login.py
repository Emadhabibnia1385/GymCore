"""«Log in with the bot»: the web panel asks, the person approves inside Telegram.

1. The browser starts a request and gets a link `t.me/<bot>?start=wl_<token>` plus a private
   `secret` it keeps and polls with.
2. The person opens the link; the bot shows who is asking (device, time, address) and two
   buttons. Approving binds the request to that Telegram account.
3. The browser's next poll gets its session, once.

No password and no telegram.org script. The approval message is the defence against someone
sending a victim their own link: the victim sees the asking device and can refuse.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Person, WebLoginRequest

TTL = timedelta(minutes=5)
PENDING, APPROVED, DENIED, CONSUMED = "PENDING", "APPROVED", "DENIED", "CONSUMED"
START_PREFIX = "wl_"
LINK_PREFIX = "wk_"  # «connect Telegram», started from a signed-in web account


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(moment: datetime) -> datetime:
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


def start(db: Session, user_agent: str | None, client_ip: str | None) -> tuple[str, str]:
    """Open a request; returns (token for the bot link, secret for the browser)."""
    now = _now()
    db.execute(delete(WebLoginRequest).where(WebLoginRequest.expires_at < now - TTL))
    token, secret = secrets.token_urlsafe(18), secrets.token_urlsafe(32)
    db.add(WebLoginRequest(
        token_hash=_hash(token), secret_hash=_hash(secret),
        status=PENDING, user_agent=(user_agent or "")[:200] or None,
        client_ip=(client_ip or "")[:64] or None, expires_at=now + TTL,
    ))
    db.commit()
    return token, secret


def _by_token(db: Session, token: str) -> WebLoginRequest | None:
    return db.scalar(select(WebLoginRequest).where(WebLoginRequest.token_hash == _hash(token)))


def pending(db: Session, token: str) -> WebLoginRequest | None:
    """The request behind a bot link, while it is still waiting for an answer."""
    request = _by_token(db, token or "")
    if request is None or request.status != PENDING or _aware(request.expires_at) < _now():
        return None
    return request


def approve(db: Session, token: str, person: Person, telegram_user_id: str) -> bool:
    request = pending(db, token)
    if request is None or request.link_person_id is not None or not person.is_active:
        return False
    request.status = APPROVED
    request.person_id = person.id
    request.telegram_user_id = str(telegram_user_id)
    db.commit()
    return True


def deny(db: Session, token: str) -> bool:
    request = pending(db, token)
    if request is None:
        return False
    request.status = DENIED
    db.commit()
    return True


def claim(db: Session, secret: str) -> tuple[str, WebLoginRequest | None]:
    """The browser's poll: ("pending" | "approved" | "denied" | "expired", request).

    "approved" is returned once; the request is consumed so the session can't be taken twice.
    """
    request = db.scalar(
        select(WebLoginRequest).where(WebLoginRequest.secret_hash == _hash(secret or ""))
    )
    if request is None or request.status == CONSUMED:
        return "expired", None
    if request.status == APPROVED:
        request.status = CONSUMED
        db.commit()
        return "approved", request
    if request.status == DENIED:
        return "denied", None
    if _aware(request.expires_at) < _now():
        return "expired", None
    return "pending", None


def describe_device(user_agent: str | None) -> str:
    """«Chrome روی Mac» from a User-Agent — enough for a person to recognise their own device."""
    ua = (user_agent or "").lower()
    browser = next(
        (name for key, name in (
            ("edg/", "Edge"), ("opr/", "Opera"), ("firefox", "Firefox"), ("chrome", "Chrome"),
            ("safari", "Safari"),
        ) if key in ua),
        "مرورگر ناشناس",
    )
    system = next(
        (name for key, name in (
            ("iphone", "iPhone"), ("ipad", "iPad"), ("android", "Android"),
            ("windows", "Windows"), ("mac os", "Mac"), ("linux", "Linux"),
        ) if key in ua),
        None,
    )
    return f"{browser} روی {system}" if system else browser


# --- connecting Telegram to a username/password account ---


def start_link(db: Session, person_id: int, user_agent: str | None, client_ip: str | None) -> str:
    """Open a «connect Telegram» request for a signed-in web account; returns the bot token."""
    now = _now()
    db.execute(delete(WebLoginRequest).where(WebLoginRequest.expires_at < now - TTL))
    token = secrets.token_urlsafe(18)
    db.add(WebLoginRequest(
        token_hash=_hash(token), secret_hash=_hash(secrets.token_urlsafe(32)),  # nobody polls it
        status=PENDING, link_person_id=person_id,
        user_agent=(user_agent or "")[:200] or None,
        client_ip=(client_ip or "")[:64] or None, expires_at=now + TTL,
    ))
    db.commit()
    return token


def pending_link(db: Session, token: str) -> WebLoginRequest | None:
    request = pending(db, token)
    return request if request is not None and request.link_person_id is not None else None
