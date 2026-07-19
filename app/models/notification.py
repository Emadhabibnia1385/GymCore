"""Unified notification record — outbound messages to clients / broadcasts.

Improves on the v1 append-only reminder log: a notification carries its own
delivery lifecycle (scheduledFor / sentAt / failedAt / retryCount / lastError)
and an optional idempotency key so the worker never double-delivers. A NULL
`person_id` denotes a broadcast/system notification.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import NotificationKind, NotificationStatus
from app.models.person import Person


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        # Supports the worker's "due and not yet sent" scan.
        Index("ix_notifications_status_scheduled", "status", "scheduled_for"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # NULL = broadcast / not tied to a single person.
    person_id: Mapped[int | None] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[NotificationKind] = mapped_column(Enum(NotificationKind))
    title: Mapped[str | None] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus), default=NotificationStatus.PENDING, index=True
    )
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retry_count: Mapped[int] = mapped_column(default=0)
    last_error: Mapped[str | None] = mapped_column(String(500))
    # De-duplication guard: a stable key means "deliver at most once".
    idempotency_key: Mapped[str | None] = mapped_column(String(200), unique=True)
    created_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    person: Mapped[Person | None] = relationship()
