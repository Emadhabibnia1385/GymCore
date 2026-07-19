"""Person — the shared human identity (client / coach / admin).

A Person owns all data (courses, plans, attendance, payments). Messaging
accounts are attached via ChannelIdentity, so one person can use Telegram and
Bale interchangeably.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Role


class Person(Base):
    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.CLIENT, index=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    identities: Mapped[list["ChannelIdentity"]] = relationship(  # noqa: F821
        back_populates="person", cascade="all, delete-orphan"
    )
    courses: Mapped[list["Course"]] = relationship(  # noqa: F821
        back_populates="client", foreign_keys="Course.client_id"
    )

    def __repr__(self) -> str:
        return f"<Person {self.id} {self.name} {self.role.value}>"
