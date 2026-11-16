"""The coach's follow-ups on the web: the weekly timetable, who to call today, renewals,
leads, and the notes timeline — the bot's «📇 پیگیری‌ها» and «🗓 برنامهٔ هفتگی»."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.web_deps import require_admin
from app.core import clock
from app.core.exceptions import NotFoundError
from app.core.jalali import format_jalali
from app.db.session import get_db
from app.models import (
    FollowUp,
    Lead,
    LeadSource,
    LeadStatus,
    Person,
    Role,
    StudentType,
    WebSession,
)
from app.services import crm as crm_service
from app.services import schedule as schedule_service

router = APIRouter(prefix="/api/admin", tags=["followups"], dependencies=[Depends(require_admin)])

SOURCE_LABELS = {
    "INSTAGRAM": "اینستاگرام", "TELEGRAM": "تلگرام", "REFERRAL": "معرفی", "WALK_IN": "مراجعهٔ حضوری",
    "WEBSITE": "وب‌سایت", "OTHER": "سایر",
}
STATUS_LABELS = {
    "NEW": "جدید",
    "CONTACTED": "در تماس",
    "TRIAL": "آزمایشی",
    "WON": "شاگرد شد",
    "LOST": "از دست رفت",
}


class Saved(BaseModel):
    ok: bool = True
    message: str


def _by(session: WebSession) -> str:
    return str(session.telegram_user_id or f"web:{session.person_id}")


# --- weekly timetable ---


class TimetableEntry(BaseModel):
    time: str
    student: str
    class_title: str
    person_id: int
    course_id: int


class TimetableDay(BaseModel):
    day: int
    name: str
    entries: list[TimetableEntry]


@router.get("/timetable", response_model=list[TimetableDay], operation_id="timetable_week")
def timetable(db: Session = Depends(get_db)) -> list[TimetableDay]:
    week = schedule_service.weekly_timetable(db)
    return [
        TimetableDay(
            day=day,
            name=schedule_service.WEEKDAY_NAMES[day],
            entries=[
                TimetableEntry(
                    time=e.time, student=e.course.client.name,
                    class_title=e.course.class_type.title,
                    person_id=e.course.client_id, course_id=e.course.id,
                )
                for e in week.get(day, [])
            ],
        )
        for day in range(7)
    ]


# --- follow-ups ---


class FollowUpRow(BaseModel):
    id: int
    target: str
    person_id: int | None
    lead_id: int | None
    due: str
    due_iso: str
    days_late: int
    note: str | None


class SummaryView(BaseModel):
    due: int
    renewals: int
    leads: int
    waiting: bool


class FollowUpIn(BaseModel):
    due_on: date
    note: str | None = Field(default=None, max_length=300)
    person_id: int | None = None
    lead_id: int | None = None


class PostponeIn(BaseModel):
    days: int = Field(ge=1, le=60)


def _row(f: FollowUp, today: date) -> FollowUpRow:
    return FollowUpRow(
        id=f.id, target=crm_service.follow_up_target_name(f), person_id=f.person_id,
        lead_id=f.lead_id, due=format_jalali(f.due_on), due_iso=f.due_on.isoformat(),
        days_late=max((today - f.due_on).days, 0), note=f.note,
    )


@router.get("/followups/summary", response_model=SummaryView, operation_id="followups_summary")
def followups_summary(db: Session = Depends(get_db)) -> SummaryView:
    s = crm_service.summary(db)
    return SummaryView(due=s.due, renewals=s.renewals, leads=s.leads, waiting=s.waiting)


@router.get("/followups/due", response_model=list[FollowUpRow], operation_id="followups_due")
def followups_due(db: Session = Depends(get_db)) -> list[FollowUpRow]:
    today = clock.today()
    return [_row(f, today) for f in crm_service.list_due(db)]


@router.post("/followups", response_model=Saved, operation_id="followup_add")
def add_followup(
    body: FollowUpIn, session: WebSession = Depends(require_admin), db: Session = Depends(get_db)
) -> Saved:
    crm_service.add_follow_up(
        db, body.due_on, person_id=body.person_id, lead_id=body.lead_id, note=body.note,
        created_by=_by(session),
    )
    return Saved(message="پیگیری ثبت شد.")


@router.post("/followups/{follow_up_id}/done", response_model=Saved, operation_id="followup_done")
def followup_done(follow_up_id: int, db: Session = Depends(get_db)) -> Saved:
    crm_service.complete_follow_up(db, follow_up_id)
    return Saved(message="پیگیری انجام‌شده ثبت شد.")


@router.post(
    "/followups/{follow_up_id}/postpone", response_model=Saved, operation_id="followup_postpone"
)
def followup_postpone(follow_up_id: int, body: PostponeIn, db: Session = Depends(get_db)) -> Saved:
    crm_service.postpone_follow_up(db, follow_up_id, body.days)
    return Saved(message="پیگیری عقب افتاد.")


# --- renewals ---


class RenewalRow(BaseModel):
    person_id: int
    student: str
    course_id: int
    class_title: str
    ended: str | None
    days_since: int | None
    followed_up: bool


@router.get("/renewals", response_model=list[RenewalRow], operation_id="renewals_list")
def renewals(db: Session = Depends(get_db)) -> list[RenewalRow]:
    return [
        RenewalRow(
            person_id=r.person.id, student=r.person.name, course_id=r.course.id,
            class_title=r.course.class_type.title,
            ended=format_jalali(r.ended_on) if r.ended_on else None,
            days_since=r.days_since, followed_up=r.followed_up,
        )
        for r in crm_service.renewal_candidates(db)
    ]


# --- leads ---


class LeadView(BaseModel):
    id: int
    name: str
    phone: str | None
    source: str
    source_label: str
    interest: str | None
    status: str
    status_label: str
    note: str | None
    person_id: int | None
    existing_student: int | None
    next_follow_up: str | None


class LeadList(BaseModel):
    counts: dict[str, int]
    rows: list[LeadView]


class LeadIn(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    source: LeadSource = LeadSource.OTHER
    interest: str | None = Field(default=None, max_length=200)


class LeadPatch(BaseModel):
    status: LeadStatus | None = None
    phone: str | None = Field(default=None, max_length=30)
    note: str | None = Field(default=None, max_length=500)
    follow_up_on: date | None = None


class ConvertIn(BaseModel):
    kind: StudentType = StudentType.IN_PERSON


class Converted(BaseModel):
    person_id: int
    linked: bool
    message: str


def _lead(db: Session, lead: Lead) -> LeadView:
    follow_up = crm_service.open_lead_follow_up(lead)
    existing = crm_service.person_with_phone(db, lead.phone)
    return LeadView(
        id=lead.id, name=lead.name, phone=lead.phone, source=lead.source.value,
        source_label=SOURCE_LABELS[lead.source.value], interest=lead.interest,
        status=lead.status.value, status_label=STATUS_LABELS[lead.status.value], note=lead.note,
        person_id=lead.person_id, existing_student=existing.id if existing else None,
        next_follow_up=format_jalali(follow_up.due_on) if follow_up else None,
    )


@router.get("/leads", response_model=LeadList, operation_id="leads_list")
def leads(status: LeadStatus | None = None, db: Session = Depends(get_db)) -> LeadList:
    counts = crm_service.lead_counts(db)
    return LeadList(
        counts={s.value: n for s, n in counts.items()},
        rows=[_lead(db, lead) for lead in crm_service.list_leads(db, status)],
    )


@router.get("/leads/options", operation_id="leads_options")
def lead_options() -> dict:
    return {
        "sources": [{"value": k, "label": v} for k, v in SOURCE_LABELS.items()],
        "statuses": [{"value": k, "label": v} for k, v in STATUS_LABELS.items()],
    }


@router.post("/leads", response_model=LeadView, operation_id="lead_create")
def create_lead(
    body: LeadIn, session: WebSession = Depends(require_admin), db: Session = Depends(get_db)
) -> LeadView:
    lead = crm_service.create_lead(
        db, body.name, phone=body.phone, source=body.source, interest=body.interest,
        created_by=_by(session),
    )
    return _lead(db, lead)


@router.patch("/leads/{lead_id}", response_model=LeadView, operation_id="lead_update")
def update_lead(
    lead_id: int, body: LeadPatch, session: WebSession = Depends(require_admin),
    db: Session = Depends(get_db),
) -> LeadView:
    if body.status is not None:
        crm_service.set_lead_status(db, lead_id, body.status)
    if body.phone is not None:
        crm_service.set_lead_phone(db, lead_id, body.phone or None)
    if body.note:
        crm_service.add_lead_note(db, lead_id, body.note)
    if body.follow_up_on is not None:
        crm_service.set_lead_follow_up(db, lead_id, body.follow_up_on, created_by=_by(session))
    db.expire_all()
    return _lead(db, crm_service.get_lead(db, lead_id))


@router.post("/leads/{lead_id}/convert", response_model=Converted, operation_id="lead_convert")
def convert_lead(
    lead_id: int, body: ConvertIn, session: WebSession = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Converted:
    done = crm_service.convert_lead(db, lead_id, student_type=body.kind, created_by=_by(session))
    return Converted(
        person_id=done.person.id, linked=done.linked,
        message="به شاگرد موجود وصل شد." if done.linked else "سرنخ به شاگرد تبدیل شد.",
    )


@router.delete("/leads/{lead_id}", response_model=Saved, operation_id="lead_delete")
def delete_lead(lead_id: int, db: Session = Depends(get_db)) -> Saved:
    crm_service.delete_lead(db, lead_id)
    return Saved(message="سرنخ حذف شد.")


# --- notes timeline ---


class NoteRow(BaseModel):
    id: int
    date: str
    text: str


class NoteIn(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


def _client(db: Session, person_id: int) -> Person:
    person = db.get(Person, person_id)
    if person is None or person.role != Role.CLIENT:
        raise NotFoundError("شاگرد پیدا نشد")
    return person


@router.get("/students/{person_id}/notes", response_model=list[NoteRow], operation_id="notes_list")
def notes(person_id: int, db: Session = Depends(get_db)) -> list[NoteRow]:
    _client(db, person_id)
    return [
        NoteRow(id=n.id, date=format_jalali(crm_service.local_date(n.created_at)), text=n.text)
        for n in crm_service.list_notes(db, person_id)
    ]


@router.post("/students/{person_id}/notes", response_model=Saved, operation_id="note_add")
def add_note(
    person_id: int, body: NoteIn, session: WebSession = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Saved:
    _client(db, person_id)
    crm_service.add_note(db, person_id, body.text, created_by=_by(session))
    return Saved(message="یادداشت ثبت شد.")
