"""The coach's side of the web panel: students and their profiles.

Reads come from the same services as the in-bot panel. Every route needs an admin
(`require_admin`), so a student's session gets a 403 however they craft the URL.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.web_deps import require_admin
from app.api.web_student import (
    CourseDetail,
    CourseSummary,
    PackageView,
    ProgramView,
    course_detail,
    course_summary,
    program_view,
)
from app.core.exceptions import ConflictError, ValidationError
from app.core.jalali import format_jalali
from app.db.session import get_db
from app.models import Course, Person, Platform, Role, StudentType
from app.services import courses as courses_service
from app.services import crm as crm_service
from app.services import packages as packages_service
from app.services import payments as payments_service
from app.services import plans as plans_service
from app.services import roster as roster_service
from app.services import web_accounts

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


class StudentRow(BaseModel):
    id: int
    name: str
    kind: str  # "IN_PERSON" | "ONLINE"
    state: str  # active | ended | none | online
    remaining: int | None
    programs: int
    packages: int


class StudentList(BaseModel):
    in_person: int
    online: int
    rows: list[StudentRow]


class PaymentRow(BaseModel):
    id: int
    amount: int
    date: str
    kind: str
    note: str | None


class StudentProfile(BaseModel):
    id: int
    name: str
    phone: str | None
    phone2: str | None
    kind: str
    on_telegram: bool
    on_bale: bool
    courses: list[CourseSummary]
    paid: int
    owing: int
    payments: list[PaymentRow]
    programs: list[ProgramView]
    packages: list[PackageView]
    notes: int
    username: str | None


@router.get("/students", response_model=StudentList, operation_id="admin_students")
def students(
    kind: str | None = Query(default=None, pattern="^(IN_PERSON|ONLINE)$"),
    q: str | None = Query(default=None, max_length=80),
    db: Session = Depends(get_db),
) -> StudentList:
    totals = roster_service.counts(db)
    rows = roster_service.list_students(db, StudentType[kind] if kind else None, q)
    return StudentList(
        in_person=totals[StudentType.IN_PERSON],
        online=totals[StudentType.ONLINE],
        rows=[
            StudentRow(
                id=r.person.id, name=r.person.name, kind=r.person.student_type.value,
                state=r.state, remaining=r.remaining, programs=r.programs, packages=r.packages,
            )
            for r in rows
        ],
    )


def _student(db: Session, person_id: int) -> Person:
    person = db.get(Person, person_id)
    if person is None or person.role != Role.CLIENT:
        raise HTTPException(status_code=404, detail="موردی پیدا نشد")
    return person


@router.get("/students/{person_id}", response_model=StudentProfile, operation_id="admin_student")
def student(person_id: int, db: Session = Depends(get_db)) -> StudentProfile:
    person = _student(db, person_id)
    courses = courses_service.list_courses(db, client_id=person.id)
    owing = sum(payments_service.course_balance(db, c)["outstanding"] for c in courses)
    platforms = {i.platform for i in person.identities}
    return StudentProfile(
        id=person.id, name=person.name, phone=person.phone, phone2=person.phone2,
        kind=person.student_type.value,
        on_telegram=Platform.TELEGRAM in platforms, on_bale=Platform.BALE in platforms,
        courses=[course_summary(db, c) for c in courses],
        paid=payments_service.total_paid_person(db, person.id),
        owing=owing,
        payments=[
            PaymentRow(
                id=p.id, amount=p.amount, date=format_jalali(p.paid_at), kind=p.kind.value,
                note=p.note,
            )
            for p in payments_service.list_payments(db, person_id=person.id)[:20]
        ],
        programs=[
            program_view(a) for a in plans_service.list_assignments(db, person_id=person.id)
        ],
        packages=[
            PackageView(id=p.id, title=p.title, description=p.description, items=n)
            for p, n in (
                (p, packages_service.item_counts(db, [p.id]).get(p.id, 0))
                for p in packages_service.list_for_person(db, person.id)
            )
        ],
        notes=crm_service.count_notes(db, person.id),
        username=web_accounts.username_of(db, person.id),
    )


@router.get("/courses/{course_id}", response_model=CourseDetail, operation_id="admin_course")
def course(course_id: int, db: Session = Depends(get_db)) -> CourseDetail:
    found = db.get(Course, course_id)
    if found is None:
        raise HTTPException(status_code=404, detail="موردی پیدا نشد")
    return course_detail(db, found)


class WebAccess(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=200)


class Done(BaseModel):
    ok: bool = True
    message: str


@router.post(
    "/students/{person_id}/web-access", response_model=Done, operation_id="admin_web_access"
)
def give_web_access(person_id: int, body: WebAccess, db: Session = Depends(get_db)) -> Done:
    """The coach creates a student's panel login, or resets it (the student then changes it)."""
    person = _student(db, person_id)
    try:
        web_accounts.set_credentials(db, person.id, body.username, body.password)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return Done(message="دسترسی پنل برای این شاگرد ساخته شد.")
