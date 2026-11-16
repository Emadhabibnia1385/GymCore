"""The coach's management screens on the web: students, courses, and the class catalog.

Thin calls into the services the bot's buttons use. Two places are deliberately
stricter than the bot, because the web has no confirmation dialog to fall back on:
a student with recorded payments can't be deleted here (deleting removes their
payments and rewrites past money reports), and a class in use can't be deleted.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.web_deps import require_admin
from app.api.web_student import CourseSummary, course_summary
from app.bots.common import formatting
from app.core import clock
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.db.session import get_db
from app.models import CourseStatus, Person, Role, StudentType
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import notifications as notify_service
from app.services import payments as payments_service
from app.services import persons as persons_service
from app.services import schedule as schedule_service

router = APIRouter(prefix="/api/admin", tags=["manage"], dependencies=[Depends(require_admin)])


class Created(BaseModel):
    id: int
    message: str


class Saved(BaseModel):
    ok: bool = True
    message: str


# --- students ---


class StudentIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    phone2: str | None = Field(default=None, max_length=30)
    kind: StudentType = StudentType.IN_PERSON


class StudentPatch(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=30, description="empty text removes it")
    phone2: str | None = Field(default=None, max_length=30)
    kind: StudentType | None = None


def _student(db: Session, person_id: int) -> Person:
    person = db.get(Person, person_id)
    if person is None or person.role != Role.CLIENT:
        raise NotFoundError("شاگرد پیدا نشد")
    return person


@router.post("/students", response_model=Created, operation_id="student_create")
def create_student(body: StudentIn, db: Session = Depends(get_db)) -> Created:
    person = persons_service.create(
        db, name=body.name, phone=body.phone or None, student_type=body.kind
    )
    if body.phone2:
        persons_service.update(db, person.id, phone2=body.phone2)
    return Created(id=person.id, message="شاگرد اضافه شد.")


@router.patch("/students/{person_id}", response_model=Saved, operation_id="student_update")
def update_student(person_id: int, body: StudentPatch, db: Session = Depends(get_db)) -> Saved:
    person = _student(db, person_id)
    persons_service.update(
        db, person.id, name=body.name, phone=body.phone, phone2=body.phone2,
        student_type=body.kind,
    )
    return Saved(message="اطلاعات شاگرد ذخیره شد.")


@router.delete("/students/{person_id}", response_model=Saved, operation_id="student_delete")
def delete_student(person_id: int, db: Session = Depends(get_db)) -> Saved:
    person = _student(db, person_id)
    if payments_service.total_paid_person(db, person.id) or payments_service.list_payments(
        db, person_id=person.id
    ):
        raise ConflictError(
            "این شاگرد پرداخت ثبت‌شده دارد و حذفش پرداخت‌ها و گزارش‌های مالی گذشته را عوض می‌کند. "
            "اگر واقعاً لازم است، از ربات حذفش کن."
        )
    persons_service.delete(db, person.id)
    return Saved(message="شاگرد حذف شد.")


# --- courses ---


class CourseIn(BaseModel):
    client_id: int
    class_type_id: int
    sessions_total: int = Field(ge=1, le=200)
    tuition: int = Field(default=0, ge=0, le=10**12)
    gym_fee: int = Field(default=0, ge=0, le=10**12)
    allowed_absence: int = Field(default=0, ge=0, le=100, description="0 means no limit")
    start_date: date
    weekdays: list[int] = Field(min_length=1, description="Persian weekday indexes, شنبه = 0")
    class_times: dict[int, str] = Field(default_factory=dict, description="weekday → HH:MM")


class CoursePatch(BaseModel):
    tuition: int | None = Field(default=None, ge=0, le=10**12)
    gym_fee: int | None = Field(default=None, ge=0, le=10**12)
    allowed_absence: int | None = Field(default=None, ge=0, le=100)
    weekdays: list[int] | None = Field(default=None, min_length=1)
    class_times: dict[int, str] | None = None


class StatusIn(BaseModel):
    status: CourseStatus


def _weekdays(days: list[int]) -> str:
    if any(not 0 <= d <= 6 for d in days):
        raise ValidationError("روز هفته نامعتبر است")
    return schedule_service.format_weekdays(set(days))


def _times(times: dict[int, str], days: list[int]) -> str | None:
    clean = {d: t.strip() for d, t in times.items() if t.strip() and d in days}
    return schedule_service.format_day_times(clean) or None


def _report(db: Session, course) -> None:
    """DM the student the attendance record of a course that is ending."""
    text = formatting.format_attendance_report(db, course)
    if text:
        notify_service.notify_person(db, course.client, text)


@router.post("/courses", response_model=Created, operation_id="course_create")
def create_course(body: CourseIn, db: Session = Depends(get_db)) -> Created:
    _student(db, body.client_id)
    classes_service.get(db, body.class_type_id)
    course = courses_service.create(
        db, client_id=body.client_id, class_type_id=body.class_type_id,
        sessions_total=body.sessions_total, tuition=body.tuition, gym_fee=body.gym_fee,
        allowed_absence=body.allowed_absence, start_date=body.start_date,
        weekdays=_weekdays(body.weekdays), class_times=_times(body.class_times, body.weekdays),
    )
    return Created(id=course.id, message="دوره ساخته شد.")


@router.patch("/courses/{course_id}", response_model=CourseSummary, operation_id="course_update")
def update_course(
    course_id: int, body: CoursePatch, db: Session = Depends(get_db)
) -> CourseSummary:
    course = courses_service.get(db, course_id)
    if body.tuition is not None or body.gym_fee is not None:
        courses_service.set_fees(db, course.id, tuition=body.tuition, gym_fee=body.gym_fee)
    if body.allowed_absence is not None:
        courses_service.set_allowed_absence(db, course.id, body.allowed_absence)
    if body.weekdays is not None:
        courses_service.set_weekdays(db, course.id, _weekdays(body.weekdays))
    if body.class_times is not None or body.weekdays is not None:
        days = body.weekdays or schedule_service.parse_weekdays(course.weekdays)
        times = body.class_times
        if times is None:
            times = schedule_service.parse_day_times(course.class_times)
        courses_service.set_class_times(db, course.id, _times(times, days))
    db.expire_all()
    return course_summary(db, courses_service.get(db, course.id))


@router.post("/courses/{course_id}/status", response_model=Saved, operation_id="course_status")
def set_course_status(course_id: int, body: StatusIn, db: Session = Depends(get_db)) -> Saved:
    courses_service.set_status(db, course_id, body.status)
    if body.status == CourseStatus.FINISHED:
        _report(db, courses_service.get(db, course_id))
    return Saved(message="وضعیت دوره عوض شد.")


@router.post("/courses/{course_id}/renew", response_model=Created, operation_id="course_renew")
def renew_course(course_id: int, db: Session = Depends(get_db)) -> Created:
    """One-tap تمدید with the same terms: a fresh course, sessions from zero."""
    old = courses_service.get(db, course_id)
    credit = courses_service.coach_cancel_credit(db, old)
    _report(db, old)
    new = courses_service.renew(
        db, course_id, sessions_total=old.sessions_total, tuition=old.tuition,
        gym_fee=old.gym_fee, allowed_absence=old.allowed_absence, carry_credit=False,
        start_date=clock.today(),
    )
    message = "دوره با همین شرایط تمدید شد."
    if credit > 0:
        message += f" اعتبار جلسات لغوشدهٔ مربی ({credit:,} تومان) روی دورهٔ تازه آمد."
    return Created(id=new.id, message=message)


@router.delete("/courses/{course_id}", response_model=Saved, operation_id="course_delete")
def delete_course(course_id: int, db: Session = Depends(get_db)) -> Saved:
    courses_service.delete(db, course_id)
    return Saved(message="دوره حذف شد؛ تاریخچهٔ جلسات پاک شد و پرداخت‌ها ماندند.")


# --- the class catalog ---


class ClassView(BaseModel):
    id: int
    title: str
    active: bool


class ClassIn(BaseModel):
    title: str = Field(min_length=1, max_length=150)


class ClassPatch(BaseModel):
    title: str | None = Field(default=None, max_length=150)
    active: bool | None = None


@router.get("/classes", response_model=list[ClassView], operation_id="classes_list")
def list_classes(db: Session = Depends(get_db)) -> list[ClassView]:
    items = classes_service.list_class_types(db)
    return [ClassView(id=c.id, title=c.title, active=c.active) for c in items]


@router.post("/classes", response_model=Created, operation_id="class_create")
def create_class(body: ClassIn, db: Session = Depends(get_db)) -> Created:
    created = classes_service.create(db, title=body.title)
    return Created(id=created.id, message="کلاس ساخته شد.")


@router.patch("/classes/{class_id}", response_model=Saved, operation_id="class_update")
def update_class(class_id: int, body: ClassPatch, db: Session = Depends(get_db)) -> Saved:
    if body.title is not None:
        classes_service.update(db, class_id, title=body.title)
    if body.active is not None:
        classes_service.set_active(db, class_id, body.active)
    return Saved(message="ذخیره شد.")


@router.delete("/classes/{class_id}", response_model=Saved, operation_id="class_delete")
def delete_class(class_id: int, db: Session = Depends(get_db)) -> Saved:
    classes_service.delete(db, class_id)  # refuses a class a course uses
    return Saved(message="کلاس حذف شد.")
