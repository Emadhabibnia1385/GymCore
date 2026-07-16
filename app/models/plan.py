"""Training / nutrition / custom plans assigned to clients."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PlanType
from app.models.person import Person


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), index=True)
    plan_type: Mapped[PlanType] = mapped_column(Enum(PlanType))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    # Stored filename inside settings.upload_dir (PDF/image attachment).
    file_path: Mapped[str | None] = mapped_column(String(300))
    original_filename: Mapped[str | None] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    person: Mapped[Person] = relationship()
