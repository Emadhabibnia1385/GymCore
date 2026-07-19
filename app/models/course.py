"""A course: one client enrolled in one class type for N paid sessions.

IMPORTANT business rule: remaining sessions are NEVER stored — they are always
computed from the append-only attendance history
(see services/courses.py::remaining_sessions).

Per-person financial and attendance terms (tuition, gym fee, allowed absence)
are LOCKED on the course so that later changes to catalog defaults never
rewrite historical agreements.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.class_type import ClassType
from app.models.enums import CourseStatus
from app.models.person import Person


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), index=True)
    class_type_id: Mapped[int] = mapped_column(ForeignKey("class_types.id"), index=True)
    sessions_total: Mapped[int] = mapped_column()
    # Amounts are stored in Toman as integers (no floating point for money).
    tuition: Mapped[int] = mapped_column(BigInteger, default=0)
    gym_fee: Mapped[int] = mapped_column(BigInteger, default=0)
    # Number of excused (allowed) absences included in this course's terms.
    allowed_absence: Mapped[int] = mapped_column(default=0)
    # Client declared upcoming travel/leave (affects coach planning, not billing).
    travel_declared: Mapped[bool] = mapped_column(default=False)
    start_date: Mapped[date] = mapped_column(Date)
    status: Mapped[CourseStatus] = mapped_column(
        Enum(CourseStatus), default=CourseStatus.ACTIVE, index=True
    )
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    client: Mapped[Person] = relationship(
        back_populates="courses", foreign_keys=[client_id]
    )
    class_type: Mapped[ClassType] = relationship()
    attendance_events: Mapped[list["AttendanceEvent"]] = relationship(  # noqa: F821
        back_populates="course", order_by="AttendanceEvent.session_date"
    )
