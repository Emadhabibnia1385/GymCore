"""Follow-ups for the coach — «📇 پیگیری‌ها»: leads, a notes timeline per
student, dated follow-ups, and who should renew.

Nothing here writes attendance, courses or payments. A renewal candidate's end
date is derived from the append-only attendance history (the latest event per
session date wins — courses.effective_status_map), because a course has no
finish timestamp.

"Today" is the coach's calendar day in the configured timezone
(`TIMEZONE`, Asia/Tehran), so «فردا» tapped at 01:00 lands on the right day
whatever clock the server keeps.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, aliased, selectinload

from app.copy import crm_texts as C
from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.core.jalali import format_jalali
from app.core.phone import is_valid_phone, normalize_phone
from app.models import (
    OPEN_LEAD_STATUSES,
    AttendanceStatus,
    Course,
    CourseStatus,
    FollowUp,
    Lead,
    LeadSource,
    LeadStatus,
    Person,
    PersonNote,
    Role,
    StudentType,
)
from app.services import courses as courses_service
from app.services import persons as persons_service

_NAME_MAX = 150  # Lead.name
_INTEREST_MAX = 200  # Lead.interest
# A follow-up is due within a year; past that it is a mistyped Jalali year.
_MAX_AHEAD = timedelta(days=365)
# Iran has kept standard time all year since 2022 — the fallback when the
# server has no tz database.
_TEHRAN = timezone(timedelta(hours=3, minutes=30), "Asia/Tehran")


# --- dates ---


@lru_cache
def _zone(name: str):
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return _TEHRAN


def local_now(now: datetime | None = None) -> datetime:
    """`now` in the coach's timezone. A naive datetime is UTC, as stored by the
    database (CURRENT_TIMESTAMP) and the notification ledger."""
    moment = now or datetime.now(UTC)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    return moment.astimezone(_zone(get_settings().timezone))


def local_today(now: datetime | None = None) -> date:
    return local_now(now).date()


def local_date(moment: datetime) -> date:
    """The coach's calendar day of a stored timestamp."""
    return local_now(moment).date()


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def check_due(due_on: date, today: date | None = None) -> None:
    """A follow-up is due from today to a year ahead — anything else is a typo."""
    today = today or local_today()
    if not today <= due_on <= today + _MAX_AHEAD:
        raise ValidationError(C.ERR_DUE_RANGE)


# --- input cleaning (shared by the admin prompts and the service) ---


def clean_name(name: str | None) -> str:
    name = (name or "").strip()
    if not name:
        raise ValidationError(C.ERR_NAME_REQUIRED)
    if len(name) > _NAME_MAX:
        raise ValidationError(C.ERR_NAME_TOO_LONG.format(n=_NAME_MAX))
    return name


def clean_phone(raw: str | None) -> str | None:
    """A typed phone (Persian digits, +98…) as 09xxxxxxxxx; None when blank."""
    if raw is None or not raw.strip():
        return None
    phone = normalize_phone(raw)
    if not is_valid_phone(phone):
        raise ValidationError(C.ERR_PHONE_INVALID)
    return phone


def clean_interest(text: str | None) -> str | None:
    text = (text or "").strip()
    if len(text) > _INTEREST_MAX:
        raise ValidationError(C.ERR_INTEREST_TOO_LONG.format(n=_INTEREST_MAX))
    return text or None


# --- leads ---


def get_lead(db: Session, lead_id: int) -> Lead:
    lead = db.get(Lead, lead_id)
    if lead is None:
        raise NotFoundError(C.ERR_LEAD_NOT_FOUND)
    return lead


def create_lead(
    db: Session,
    name: str,
    phone: str | None = None,
    source: LeadSource = LeadSource.OTHER,
    interest: str | None = None,
    created_by: str | None = None,
) -> Lead:
    lead = Lead(
        name=clean_name(name),
        phone=clean_phone(phone),
        source=source,
        interest=clean_interest(interest),
        created_by=created_by,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def list_leads(db: Session, status: LeadStatus | None = None) -> list[Lead]:
    """Open leads soonest follow-up first (none scheduled last, newest first);
    closed ones most recently changed first."""
    stmt = select(Lead).options(selectinload(Lead.person))
    if status is not None:
        stmt = stmt.where(Lead.status == status)
    leads = list(db.scalars(stmt))
    if status is not None and status not in OPEN_LEAD_STATUSES:
        return sorted(leads, key=lambda lead: (lead.updated_at, lead.id), reverse=True)
    return sorted(
        leads,
        key=lambda lead: (
            lead.next_follow_up is None,
            lead.next_follow_up or date.max,
            -lead.id,
        ),
    )


def lead_counts(db: Session) -> dict[LeadStatus, int]:
    counts = dict.fromkeys(LeadStatus, 0)
    for status, count in db.execute(select(Lead.status, func.count()).group_by(Lead.status)):
        counts[status] = count
    return counts


def count_open_leads(db: Session) -> int:
    counts = lead_counts(db)
    return sum(counts[status] for status in OPEN_LEAD_STATUSES)


def person_with_phone(db: Session, phone: str | None) -> Person | None:
    """The student a lead's phone already belongs to, if any."""
    return persons_service.get_by_phone(db, phone) if phone else None


def is_converted(lead: Lead) -> bool:
    """WON and still pointing at its student (a deleted student unlinks it)."""
    return lead.status == LeadStatus.WON and lead.person_id is not None


def add_lead_note(db: Session, lead_id: int, text: str, on: date | None = None) -> Lead:
    """Append what was said as a dated line — earlier lines are never rewritten."""
    text = (text or "").strip()
    if not text:
        raise ValidationError(C.ERR_NOTE_EMPTY)
    lead = get_lead(db, lead_id)
    line = C.LEAD_NOTE_LINE.format(date=format_jalali(on or local_today()), text=text)
    lead.note = f"{lead.note}\n{line}" if lead.note else line
    db.commit()
    db.refresh(lead)
    return lead


def set_lead_phone(db: Session, lead_id: int, phone: str | None) -> Lead:
    """Change the phone; blank clears it."""
    lead = get_lead(db, lead_id)
    lead.phone = clean_phone(phone)
    db.commit()
    db.refresh(lead)
    return lead


def set_lead_status(db: Session, lead_id: int, status: LeadStatus) -> Lead:
    """Move a lead between NEW / CONTACTED / TRIAL / LOST.

    WON only comes from :func:`convert_lead`, and a converted lead stays WON.
    LOST closes the lead's open follow-up — nobody is chased after giving up.
    """
    lead = get_lead(db, lead_id)
    if is_converted(lead):
        raise ValidationError(C.ERR_LEAD_CONVERTED)
    if status == LeadStatus.WON:
        raise ValidationError(C.ERR_USE_CONVERT)
    lead.status = status
    if status == LeadStatus.LOST:
        for follow_up in lead.follow_ups:
            if not follow_up.done:
                _close(follow_up)
        _sync_lead(lead)
    db.commit()
    db.refresh(lead)
    return lead


def open_lead_follow_up(lead: Lead) -> FollowUp | None:
    pending = [f for f in lead.follow_ups if not f.done]
    # A follow-up added in this session has no id until it is flushed.
    return min(pending, key=lambda f: (f.due_on, f.id or 0)) if pending else None


def set_lead_follow_up(
    db: Session,
    lead_id: int,
    due_on: date,
    today: date | None = None,
    created_by: str | None = None,
) -> FollowUp:
    """A lead has one next follow-up: move it to `due_on`, or create it."""
    lead = get_lead(db, lead_id)
    if lead.status not in OPEN_LEAD_STATUSES:
        raise ValidationError(C.ERR_LEAD_CLOSED)
    check_due(due_on, today)
    follow_up = open_lead_follow_up(lead)
    if follow_up is None:
        follow_up = FollowUp(lead=lead, due_on=due_on, done=False, created_by=created_by)
        db.add(follow_up)
    else:
        follow_up.due_on = due_on
    _sync_lead(lead)
    db.commit()
    db.refresh(follow_up)
    return follow_up


@dataclass(frozen=True)
class Conversion:
    lead: Lead
    person: Person
    linked: bool  # the lead's phone already belonged to this student


def convert_lead(
    db: Session,
    lead_id: int,
    student_type: StudentType = StudentType.IN_PERSON,
    created_by: str | None = None,
) -> Conversion:
    """Make the lead a student (status WON, `person_id` set).

    A phone that already belongs to a student links the lead to that student
    instead of failing. The lead's open follow-up moves to the student, and how
    they came in (source, interest, the lead's notes) opens their timeline.
    Converting twice changes nothing.
    """
    lead = get_lead(db, lead_id)
    if is_converted(lead):
        return Conversion(lead, persons_service.get(db, lead.person_id), linked=False)
    try:
        person = persons_service.create(
            db, name=lead.name, phone=lead.phone, role=Role.CLIENT, student_type=student_type
        )
        linked = False
    except ConflictError:
        person = persons_service.get_by_phone(db, lead.phone)
        linked = True
    lead.person = person
    lead.status = LeadStatus.WON
    for follow_up in list(lead.follow_ups):
        if not follow_up.done:
            follow_up.lead = None
            follow_up.person = person
    _sync_lead(lead)
    db.add(PersonNote(person=person, text=_conversion_note(lead), created_by=created_by))
    db.commit()
    db.refresh(lead)
    return Conversion(lead, person, linked)


def _conversion_note(lead: Lead) -> str:
    lines = [C.CONVERTED_NOTE.format(source=C.SOURCE_LABELS[lead.source.value])]
    if lead.interest:
        lines.append(C.CONVERTED_NOTE_INTEREST.format(interest=lead.interest))
    if lead.note:
        lines.append(lead.note)
    return "\n".join(lines)


def delete_lead(db: Session, lead_id: int) -> None:
    """Remove a lead entered by mistake, with its follow-ups."""
    db.delete(get_lead(db, lead_id))
    db.commit()


def _sync_lead(lead: Lead) -> None:
    """Keep `Lead.next_follow_up` equal to its open follow-up's date."""
    follow_up = open_lead_follow_up(lead)
    lead.next_follow_up = follow_up.due_on if follow_up else None


# --- notes (a student's timeline — append-only) ---


def add_note(
    db: Session, person_id: int, text: str, created_by: str | None = None
) -> PersonNote:
    text = (text or "").strip()
    if not text:
        raise ValidationError(C.ERR_NOTE_EMPTY)
    persons_service.get(db, person_id)
    note = PersonNote(person_id=person_id, text=text, created_by=created_by)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def list_notes(db: Session, person_id: int, limit: int | None = None) -> list[PersonNote]:
    """The student's timeline, newest first."""
    stmt = (
        select(PersonNote)
        .where(PersonNote.person_id == person_id)
        .order_by(PersonNote.created_at.desc(), PersonNote.id.desc())
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt))


def count_notes(db: Session, person_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(PersonNote).where(PersonNote.person_id == person_id)
    ) or 0


# --- follow-ups ---


def get_follow_up(db: Session, follow_up_id: int) -> FollowUp:
    follow_up = db.get(FollowUp, follow_up_id)
    if follow_up is None:
        raise NotFoundError(C.ERR_FOLLOW_UP_NOT_FOUND)
    return follow_up


def add_follow_up(
    db: Session,
    due_on: date,
    person_id: int | None = None,
    lead_id: int | None = None,
    note: str | None = None,
    created_by: str | None = None,
    today: date | None = None,
) -> FollowUp:
    """Schedule contacting one student or one lead (exactly one of the two)."""
    if (person_id is None) == (lead_id is None):
        raise ValidationError(C.ERR_FOLLOW_UP_TARGET)
    check_due(due_on, today)
    follow_up = FollowUp(
        due_on=due_on, note=(note or "").strip() or None, done=False, created_by=created_by
    )
    if person_id is not None:
        follow_up.person = persons_service.get(db, person_id)
    else:
        lead = get_lead(db, lead_id)
        if lead.status not in OPEN_LEAD_STATUSES:
            raise ValidationError(C.ERR_LEAD_CLOSED)
        follow_up.lead = lead
        _sync_lead(lead)
    db.add(follow_up)
    db.commit()
    db.refresh(follow_up)
    return follow_up


def _close(follow_up: FollowUp) -> None:
    follow_up.done = True
    follow_up.done_at = _utcnow()


def complete_follow_up(db: Session, follow_up_id: int) -> FollowUp:
    """Mark it done (a second tap changes nothing)."""
    follow_up = get_follow_up(db, follow_up_id)
    if not follow_up.done:
        _close(follow_up)
        if follow_up.lead is not None:
            _sync_lead(follow_up.lead)
        db.commit()
        db.refresh(follow_up)
    return follow_up


def postpone_follow_up(
    db: Session, follow_up_id: int, days: int, today: date | None = None
) -> FollowUp:
    """Push it to `days` after today — «فردا» means tomorrow even when overdue."""
    follow_up = get_follow_up(db, follow_up_id)
    if follow_up.done:
        raise ValidationError(C.ERR_FOLLOW_UP_DONE)
    today = today or local_today()
    due_on = today + timedelta(days=days)
    check_due(due_on, today)
    follow_up.due_on = due_on
    if follow_up.lead is not None:
        _sync_lead(follow_up.lead)
    db.commit()
    db.refresh(follow_up)
    return follow_up


def _due_filter(today: date):
    return FollowUp.done.is_(False), FollowUp.due_on <= today


def list_due(db: Session, today: date | None = None) -> list[FollowUp]:
    """Open follow-ups due today or overdue, most overdue first."""
    return list(
        db.scalars(
            select(FollowUp)
            .options(selectinload(FollowUp.person), selectinload(FollowUp.lead))
            .where(*_due_filter(today or local_today()))
            .order_by(FollowUp.due_on, FollowUp.id)
        )
    )


def count_due(db: Session, today: date | None = None) -> int:
    return db.scalar(
        select(func.count()).select_from(FollowUp).where(*_due_filter(today or local_today()))
    ) or 0


def open_follow_ups(db: Session, person_id: int) -> list[FollowUp]:
    """The student's follow-ups not done yet, soonest first."""
    return list(
        db.scalars(
            select(FollowUp)
            .where(FollowUp.person_id == person_id, FollowUp.done.is_(False))
            .order_by(FollowUp.due_on, FollowUp.id)
        )
    )


def follow_up_target_name(follow_up: FollowUp) -> str:
    target = follow_up.person or follow_up.lead
    return target.name if target is not None else ""


# --- renewals ---


@dataclass(frozen=True)
class RenewalCandidate:
    person: Person
    course: Course  # their latest course — finished
    ended_on: date | None  # its last effective session; None when none was recorded
    days_since: int | None
    followed_up: bool  # a note or follow-up recorded since it ended


def course_end_date(db: Session, course: Course) -> date | None:
    """The day a course ended: its last effective attendance date. A MOVED date
    was vacated (the session went elsewhere), so it is not a session that happened."""
    effective = courses_service.effective_status_map(db, course.id)
    dates = [day for day, status in effective.items() if status != AttendanceStatus.MOVED]
    return max(dates) if dates else None


def renewal_candidates(
    db: Session, today: date | None = None, person_id: int | None = None
) -> list[RenewalCandidate]:
    """Students with no ACTIVE course whose latest course is FINISHED — the
    ones to call about renewing. Most recently ended first."""
    today = today or local_today()
    latest, active = aliased(Course), aliased(Course)
    stmt = (
        select(Course)
        .join(Person, Person.id == Course.client_id)
        .options(selectinload(Course.client), selectinload(Course.class_type))
        .where(
            Person.role == Role.CLIENT,
            Course.status == CourseStatus.FINISHED,
            Course.id.in_(select(func.max(latest.id)).group_by(latest.client_id)),
            ~exists().where(
                active.client_id == Course.client_id, active.status == CourseStatus.ACTIVE
            ),
        )
    )
    if person_id is not None:
        stmt = stmt.where(Course.client_id == person_id)
    candidates = []
    for course in db.scalars(stmt):
        ended_on = course_end_date(db, course)
        candidates.append(
            RenewalCandidate(
                person=course.client,
                course=course,
                ended_on=ended_on,
                days_since=(today - ended_on).days if ended_on else None,
                followed_up=_contacted_since(db, course.client_id, ended_on or course.start_date),
            )
        )
    candidates.sort(
        key=lambda c: (
            c.ended_on is None,
            -(c.ended_on or date.min).toordinal(),
            c.person.name,
        )
    )
    return candidates


def renewal_candidate(
    db: Session, person_id: int, today: date | None = None
) -> RenewalCandidate | None:
    found = renewal_candidates(db, today, person_id=person_id)
    return found[0] if found else None


def _contacted_since(db: Session, person_id: int, since: date) -> bool:
    """Whether the coach wrote a note or set a follow-up for them on or after `since`."""
    for column, owner in (
        (PersonNote.created_at, PersonNote.person_id),
        (FollowUp.created_at, FollowUp.person_id),
    ):
        latest = db.scalar(select(func.max(column)).where(owner == person_id))
        if latest is not None and local_date(latest) >= since:
            return True
    return False


# --- the front page / morning digest ---


@dataclass(frozen=True)
class Summary:
    due: int  # follow-ups due today or overdue
    renewals: int  # renewal candidates
    leads: int  # open leads
    # Something needs the coach: a follow-up is due, a course ended with nobody
    # following up, or a new lead has neither been contacted nor scheduled.
    waiting: bool


def summary(db: Session, today: date | None = None) -> Summary:
    today = today or local_today()
    due = count_due(db, today)
    candidates = renewal_candidates(db, today)
    open_leads = list(db.scalars(select(Lead).where(Lead.status.in_(OPEN_LEAD_STATUSES))))
    waiting = (
        due > 0
        or any(not c.followed_up for c in candidates)
        or any(
            lead.status == LeadStatus.NEW and lead.next_follow_up is None for lead in open_leads
        )
    )
    return Summary(due=due, renewals=len(candidates), leads=len(open_leads), waiting=waiting)
