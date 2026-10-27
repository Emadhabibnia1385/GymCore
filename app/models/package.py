"""Program packages — a bundle the coach builds once and sends to many students.

A package is the coach's course material: a diet PDF, several training videos
and some text, in order. It is sent to students as a `PackageAssignment`, and
what a student sees is LIVE: they open the package's *current* items, so a video
added later reaches everyone who already has it.

A file item keeps one `file_id` per platform, because a `file_id` only works on
the platform that issued it. The coach sends the file from one bot and, to reach
students on the other messenger, the same file once more from the other bot.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.db.base import Base
from app.models.person import Person


class ProgramPackage(Base):
    __tablename__ = "program_packages"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(150))
    # Shown to the student above the package's items.
    description: Mapped[str | None] = mapped_column(Text)
    # An inactive package is hidden from every student; its assignments stay.
    active: Mapped[bool] = mapped_column(default=True, index=True)
    created_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PackageItem(Base):
    __tablename__ = "package_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    package_id: Mapped[int] = mapped_column(
        ForeignKey("program_packages.id", ondelete="CASCADE"), index=True
    )
    sort_order: Mapped[int] = mapped_column(default=0)
    # The label on the student's button; derived from the text when unset.
    title: Mapped[str | None] = mapped_column(String(150))
    # "document" / "photo" / "video" pick the send method; "text" is text only.
    kind: Mapped[str] = mapped_column(String(16))
    # The text item itself, or the file's caption.
    text: Mapped[str | None] = mapped_column(Text)
    telegram_file_id: Mapped[str | None] = mapped_column(String(300))
    bale_file_id: Mapped[str | None] = mapped_column(String(300))
    original_filename: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    package: Mapped[ProgramPackage] = relationship()


class PackageAssignment(Base):
    """One student's access to one package — a single row per pair: revoking
    sets `active` off, sending again turns it back on."""

    __tablename__ = "package_assignments"
    __table_args__ = (
        UniqueConstraint("package_id", "person_id", name="uq_package_person"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    package_id: Mapped[int] = mapped_column(ForeignKey("program_packages.id"), index=True)
    person_id: Mapped[int] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"), index=True
    )
    active: Mapped[bool] = mapped_column(default=True, index=True)
    created_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    package: Mapped[ProgramPackage] = relationship()
    # The backref gives Person a cascading `package_assignments` collection, so
    # deleting a student (persons.delete → db.delete(person)) takes their access
    # rows with them. SQLite enforces no foreign keys here and may hand the
    # deleted id to the next student, who would otherwise inherit the package.
    person: Mapped[Person] = relationship(
        backref=backref("package_assignments", cascade="all, delete-orphan")
    )
