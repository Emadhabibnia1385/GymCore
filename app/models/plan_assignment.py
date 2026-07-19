"""A program delivered to a client — APPEND-ONLY history.

Assignments are never silently deleted; superseded programs are marked
inactive. A file may be stored either as an internal safe reference
(`file_path` under the upload dir) and/or as a platform `file_id` captured
when the coach uploaded it through a bot.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Platform
from app.models.person import Person
from app.models.plan_type import PlanType


class PlanAssignment(Base):
    __tablename__ = "plan_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), index=True)
    plan_type_id: Mapped[int] = mapped_column(ForeignKey("plan_types.id"), index=True)
    title: Mapped[str | None] = mapped_column(String(200))
    coach_note: Mapped[str | None] = mapped_column(Text)
    # Internal safe reference: a filename inside settings.upload_dir.
    file_path: Mapped[str | None] = mapped_column(String(300))
    original_filename: Mapped[str | None] = mapped_column(String(200))
    # Platform file identifier (Telegram/Bale) + which platform it belongs to.
    platform_file_id: Mapped[str | None] = mapped_column(String(300))
    file_platform: Mapped[Platform | None] = mapped_column(Enum(Platform))
    active: Mapped[bool] = mapped_column(default=True, index=True)
    created_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    person: Mapped[Person] = relationship()
    plan_type: Mapped[PlanType] = relationship()
