"""Follow-ups for the coach — «📇 پیگیری‌ها».

- A **Lead** is someone who asked about classes but is not a student yet. When
  they register, the lead is converted: it points at the new (or existing)
  Person and is marked WON. The row stays as the record of how they came in.
- A **PersonNote** is one entry in a student's timeline of what was said —
  append-only, like attendance: a correction is a new note.
- A **FollowUp** is "contact this student / lead on that day". Exactly one of
  `person_id` / `lead_id` is set (enforced by a CHECK constraint).

The student-side relationships are declared here as backrefs (`Person.crm_*`)
so that deleting a student (services/persons.py::delete) takes their notes and
follow-ups with it and unlinks a converted lead — on SQLite, which does not
enforce foreign keys, as well as on Postgres.

New enum columns are VARCHAR (`native_enum=False`), so a later value needs no
Postgres ALTER TYPE.
"""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, Enum, ForeignKey, String, Text, false, func
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.db.base import Base
from app.models.person import Person


class LeadSource(str, enum.Enum):
    """Where a lead heard about the coach."""

    INSTAGRAM = "INSTAGRAM"
    TELEGRAM = "TELEGRAM"
    REFERRAL = "REFERRAL"
    WALK_IN = "WALK_IN"
    WEBSITE = "WEBSITE"
    OTHER = "OTHER"


class LeadStatus(str, enum.Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    TRIAL = "TRIAL"
    WON = "WON"  # registered — the lead now points at a student (person_id)
    LOST = "LOST"


# Leads still worth chasing; WON and LOST are closed.
OPEN_LEAD_STATUSES = frozenset({LeadStatus.NEW, LeadStatus.CONTACTED, LeadStatus.TRIAL})


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    # Canonical — 09xxxxxxxxx or +<country>… (core/phone.py).
    # Not unique: someone can ask twice.
    phone: Mapped[str | None] = mapped_column(String(20), index=True)
    source: Mapped[LeadSource] = mapped_column(
        Enum(LeadSource, native_enum=False, length=20),
        default=LeadSource.OTHER,
        server_default=LeadSource.OTHER.value,
    )
    # Free text: what they asked about («کلاس فیتنس»، «برنامه غذایی»…).
    interest: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[LeadStatus] = mapped_column(
        Enum(LeadStatus, native_enum=False, length=20),
        default=LeadStatus.NEW,
        server_default=LeadStatus.NEW.value,
        index=True,
    )
    # What was said, one dated line per entry (services/crm.py::add_lead_note).
    note: Mapped[str | None] = mapped_column(Text)
    # Mirrors the lead's open follow-up, kept in step by services/crm.py.
    next_follow_up: Mapped[date | None] = mapped_column(Date)
    # Set when converted to a student.
    person_id: Mapped[int | None] = mapped_column(
        ForeignKey("persons.id", ondelete="SET NULL"), index=True
    )
    created_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Deleting the student keeps the lead (its history) and clears the link.
    person: Mapped[Person | None] = relationship(backref=backref("crm_leads"))
    follow_ups: Mapped[list["FollowUp"]] = relationship(back_populates="lead", cascade="all")


class PersonNote(Base):
    """One entry in a student's timeline — APPEND-ONLY (no edit, no delete)."""

    __tablename__ = "person_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(Text)
    # Audit: numeric platform user ID of the admin who wrote it.
    created_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    person: Mapped[Person] = relationship(backref=backref("crm_notes", cascade="all"))


class FollowUp(Base):
    __tablename__ = "follow_ups"
    __table_args__ = (
        CheckConstraint(
            "(person_id IS NULL) <> (lead_id IS NULL)", name="ck_follow_ups_one_target"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int | None] = mapped_column(
        ForeignKey("persons.id", ondelete="CASCADE"), index=True
    )
    lead_id: Mapped[int | None] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"), index=True
    )
    due_on: Mapped[date] = mapped_column(Date, index=True)
    note: Mapped[str | None] = mapped_column(Text)
    done: Mapped[bool] = mapped_column(default=False, server_default=false(), index=True)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Plain "all" cascade — no delete-orphan — so a lead's follow-up can move to
    # the student it became without being deleted on the way.
    person: Mapped[Person | None] = relationship(
        backref=backref("crm_follow_ups", cascade="all")
    )
    lead: Mapped[Lead | None] = relationship(back_populates="follow_ups")
