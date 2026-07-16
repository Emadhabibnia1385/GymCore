"""Person (client / coach / admin) and their messaging-platform identities."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import Platform, Role


class Person(Base):
    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.CLIENT, index=True)
    # Set only for people who can log into the web dashboard.
    password_hash: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
    note: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    identities: Mapped[list[ChannelIdentity]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )
    courses: Mapped[list["Course"]] = relationship(  # noqa: F821
        back_populates="client", foreign_keys="Course.client_id"
    )

    def __repr__(self) -> str:
        return f"<Person {self.id} {self.name} {self.role.value}>"


class ChannelIdentity(Base):
    """Links one messaging-platform account (or web login) to a Person."""

    __tablename__ = "channel_identities"
    __table_args__ = (
        UniqueConstraint("platform", "platform_user_id", name="uq_platform_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[Platform] = mapped_column(Enum(Platform), index=True)
    platform_user_id: Mapped[str] = mapped_column(String(64), index=True)
    person_id: Mapped[int] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    person: Mapped[Person] = relationship(back_populates="identities")
