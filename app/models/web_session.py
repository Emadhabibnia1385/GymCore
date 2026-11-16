"""A browser login for the web panel — «remember me» without keeping a password.

The browser holds a random token in an httpOnly cookie; only its SHA-256 lives
here, so a leaked database can't be replayed. A session slides forward while it
is used and expires after a stretch of disuse (services/web_auth.py).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.db.base import Base


class WebSession(Base):
    __tablename__ = "web_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), index=True)
    # The Telegram account that signed in — admin rights come from the owner
    # whitelist for this numeric id (a password session falls back to the COACH/ADMIN
    # role, which only a configured owner ever holds).
    # None for a session opened with a username and password.
    telegram_user_id: Mapped[str | None] = mapped_column(String(32))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_agent: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class WebCredential(Base):
    """A username and password for the web panel — the other way in besides Telegram.

    One per person. Only an Argon2id hash is stored. Deleting the person deletes it
    (a backref cascade, as SQLite here doesn't enforce foreign keys).
    """

    __tablename__ = "web_credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), unique=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    person = relationship(
        "Person", backref=backref("web_credential", uselist=False, cascade="all, delete-orphan")
    )


class WebLoginRequest(Base):
    """«Log in with the bot»: the browser asks, the person approves inside Telegram.

    The browser holds `secret` (to poll for the answer) and the bot link carries `token`
    (so the right person approves the right request). Only hashes are stored. The bot and
    the API are separate processes, so this table is how they talk. Short-lived.
    """

    __tablename__ = "web_login_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    secret_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # PENDING → APPROVED | DENIED → CONSUMED (the browser took its session)
    status: Mapped[str] = mapped_column(String(12), default="PENDING")
    person_id: Mapped[int | None] = mapped_column(ForeignKey("persons.id"))
    telegram_user_id: Mapped[str | None] = mapped_column(String(32))
    user_agent: Mapped[str | None] = mapped_column(String(200))
    client_ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
