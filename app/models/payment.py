"""Payment history — IMMUTABLE.

Payments are never updated or deleted. A wrong entry is corrected by recording
a compensating payment (negative amount) with a note.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.course import Course
from app.models.enums import PaymentKind
from app.models.person import Person


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), index=True)
    # Optional link to a specific course (tuition/gym fee payments).
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.id"), index=True)
    # Toman, integer. Negative amounts are corrections/refunds.
    amount: Mapped[int] = mapped_column(BigInteger)
    kind: Mapped[PaymentKind] = mapped_column(
        Enum(PaymentKind), default=PaymentKind.TUITION
    )
    method: Mapped[str | None] = mapped_column(String(100))  # e.g. کارت‌به‌کارت، نقدی
    paid_at: Mapped[date] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(String(500))
    # Audit: numeric platform user ID of the admin who recorded the payment.
    created_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    person: Mapped[Person] = relationship()
    course: Mapped[Course | None] = relationship()
