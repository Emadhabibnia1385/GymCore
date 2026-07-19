"""Log of automated reminders sent to clients — APPEND-ONLY (v1, retained).

Rows are written by the reminder worker and never updated or deleted. Retained
alongside the newer `notifications` table for audit continuity and the worker's
existing (course, kind) de-duplication query.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.course import Course
from app.models.enums import ReminderKind


class ReminderLog(Base):
    __tablename__ = "reminder_logs"
    __table_args__ = (
        # Supports the "most recent reminder for this course+kind" dedup query.
        Index("ix_reminder_course_kind", "course_id", "kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), index=True)
    kind: Mapped[ReminderKind] = mapped_column(Enum(ReminderKind))
    detail: Mapped[str | None] = mapped_column(String(200))
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    course: Mapped[Course] = relationship()
