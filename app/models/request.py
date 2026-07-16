"""Requests submitted by clients through the bots.

- ClassRegistrationRequest: "🏋️ ثبت‌نام کلاس" — admin approves → creates a Course.
- PlanRequest: "📋 سفارش برنامه" — admin fulfills → uploads a Plan.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.class_type import ClassType
from app.models.enums import PlanType, RequestStatus
from app.models.person import Person


class ClassRegistrationRequest(Base):
    __tablename__ = "class_registration_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), index=True)
    class_type_id: Mapped[int] = mapped_column(ForeignKey("class_types.id"))
    note: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus), default=RequestStatus.PENDING, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    person: Mapped[Person] = relationship()
    class_type: Mapped[ClassType] = relationship()


class PlanRequest(Base):
    __tablename__ = "plan_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), index=True)
    plan_type: Mapped[PlanType] = mapped_column(Enum(PlanType))
    note: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus), default=RequestStatus.PENDING, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    person: Mapped[Person] = relationship()
