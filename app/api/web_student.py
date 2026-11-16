"""The student's side of the web panel: their own subscription, courses, session
grid, programs and packages — and a way to ask the coach for a course.

Everything is scoped to the signed-in person; an id that isn't theirs is a 404, never
a 403, so ids reveal nothing. A student sees no money, as in the bot. Files and
videos are Telegram `file_id`s, and the Bot API can't hand a large file to a
browser, so «send to my Telegram» asks the bot to deliver them to the chat.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.web_deps import current_person
from app.bots.common import grid
from app.core.exceptions import DomainError, NotFoundError
from app.core.jalali import format_jalali
from app.db.session import get_db
from app.models import Course, CourseStatus, Person, Platform
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import crm as crm_service
from app.services import packages as packages_service
from app.services import plans as plans_service
from app.services import schedule as schedule_service

router = APIRouter(prefix="/api/me", tags=["student"])

_STATUS_LABELS = {
    CourseStatus.ACTIVE: "فعال",
    CourseStatus.FINISHED: "تمام‌شده",
    CourseStatus.PAUSED: "متوقف",
}


# --- schemas ---


class CourseSummary(BaseModel):
    id: int
    class_title: str
    status: str
    status_label: str
    start: str
    schedule: str
    total: int
    consumed: int
    remaining: int
    allowed_absence: int
    absent_allowed: int
    absent_unauthorized: int


class SlotView(BaseModel):
    iso: str
    date: str
    weekday: str
    status: str | None
    label: str
    session_no: int | None
    note: str | None


class CourseDetail(CourseSummary):
    slots: list[SlotView]


class ProgramView(BaseModel):
    id: int
    title: str
    type_title: str
    date: str
    note: str | None
    kind: str | None
    has_file: bool


class PackageView(BaseModel):
    id: int
    title: str
    description: str | None
    items: int


class PackageItemView(BaseModel):
    id: int
    title: str
    kind: str
    text: str | None
    on_telegram: bool


class PackageDetail(PackageView):
    item_list: list[PackageItemView]


class Home(BaseModel):
    name: str
    active_course: CourseSummary | None
    programs: int
    packages: int


class ClassOption(BaseModel):
    id: int
    title: str


class CourseRequest(BaseModel):
    class_type_id: int | None = None
    note: str | None = Field(default=None, max_length=500)


class Done(BaseModel):
    ok: bool = True
    message: str


# --- shared views (the coach's student screen reuses these) ---


def course_summary(db: Session, course: Course) -> CourseSummary:
    stats = schedule_service.summary(db, course)
    return CourseSummary(
        id=course.id,
        class_title=course.class_type.title,
        status=course.status.value,
        status_label=_STATUS_LABELS[course.status],
        start=format_jalali(course.start_date),
        schedule=schedule_service.class_schedule_label(course),
        total=stats["total"],
        consumed=stats["consumed"],
        remaining=stats["remaining"],
        allowed_absence=course.allowed_absence,
        absent_allowed=stats["absent_allowed"],
        absent_unauthorized=stats["absent_unauthorized"],
    )


def course_detail(db: Session, course: Course) -> CourseDetail:
    slots = schedule_service.build(db, course)
    return CourseDetail(
        **course_summary(db, course).model_dump(),
        slots=[
            SlotView(
                iso=slot.date.isoformat(),
                date=format_jalali(slot.date),
                weekday=slot.weekday,
                status=slot.status.value if slot.status else None,
                label=grid.outcome_label(slot.status),
                session_no=slot.session_no,
                note=slot.note,
            )
            for slot in slots
        ],
    )


def program_view(a) -> ProgramView:
    return ProgramView(
        id=a.id,
        title=a.title or a.plan_type.title,
        type_title=a.plan_type.title,
        date=format_jalali(a.created_at),
        note=a.coach_note,
        kind=a.file_kind,
        has_file=bool(a.platform_file_id or a.file_path),
    )


# --- routes ---


@router.get("/home", response_model=Home, operation_id="me_home")
def home(person: Person = Depends(current_person), db: Session = Depends(get_db)) -> Home:
    active = courses_service.active_course(db, person.id)
    return Home(
        name=person.name,
        active_course=course_summary(db, active) if active else None,
        programs=len(plans_service.list_assignments(db, person_id=person.id, only_active=True)),
        packages=len(packages_service.list_for_person(db, person.id)),
    )


@router.get("/courses", response_model=list[CourseSummary], operation_id="me_courses")
def my_courses(
    person: Person = Depends(current_person), db: Session = Depends(get_db)
) -> list[CourseSummary]:
    return [course_summary(db, c) for c in courses_service.list_courses(db, client_id=person.id)]


@router.get("/courses/{course_id}", response_model=CourseDetail, operation_id="me_course")
def my_course(
    course_id: int, person: Person = Depends(current_person), db: Session = Depends(get_db)
) -> CourseDetail:
    course = db.get(Course, course_id)
    if course is None or course.client_id != person.id:
        raise HTTPException(status_code=404, detail="موردی پیدا نشد")
    return course_detail(db, course)


@router.get("/programs", response_model=list[ProgramView], operation_id="me_programs")
def my_programs(
    person: Person = Depends(current_person), db: Session = Depends(get_db)
) -> list[ProgramView]:
    rows = plans_service.list_assignments(db, person_id=person.id, only_active=True)
    return [program_view(a) for a in rows]


@router.get("/packages", response_model=list[PackageView], operation_id="me_packages")
def my_packages(
    person: Person = Depends(current_person), db: Session = Depends(get_db)
) -> list[PackageView]:
    packages = packages_service.list_for_person(db, person.id)
    counts = packages_service.item_counts(db, [p.id for p in packages])
    return [
        PackageView(id=p.id, title=p.title, description=p.description, items=counts.get(p.id, 0))
        for p in packages
    ]


@router.get("/packages/{package_id}", response_model=PackageDetail, operation_id="me_package")
def my_package(
    package_id: int, person: Person = Depends(current_person), db: Session = Depends(get_db)
) -> PackageDetail:
    package = packages_service.open_for(db, package_id, person.id)
    if package is None:
        raise HTTPException(status_code=404, detail="موردی پیدا نشد")
    items = packages_service.items(db, package.id)
    return PackageDetail(
        id=package.id,
        title=package.title,
        description=package.description,
        items=len(items),
        item_list=[
            PackageItemView(
                id=i.id,
                title=packages_service.item_label(i),
                kind=i.kind,
                text=i.text,
                on_telegram=bool(packages_service.file_id_for(i, Platform.TELEGRAM)),
            )
            for i in items
        ],
    )


@router.post("/programs/{assignment_id}/send", response_model=Done, operation_id="me_program_send")
def send_program(
    assignment_id: int, person: Person = Depends(current_person), db: Session = Depends(get_db)
) -> Done:
    """Ask the bot to deliver this program to the student's Telegram chat."""
    try:
        assignment = plans_service.get_assignment(db, assignment_id)
    except NotFoundError:
        assignment = None
    if assignment is None or assignment.person_id != person.id or not assignment.active:
        raise HTTPException(status_code=404, detail="موردی پیدا نشد")
    return _deliver(lambda ctx, chat: _send_program(ctx, assignment, chat), db, person)


@router.post(
    "/packages/{package_id}/items/{item_id}/send", response_model=Done,
    operation_id="me_package_item_send",
)
def send_package_item(
    package_id: int, item_id: int,
    person: Person = Depends(current_person), db: Session = Depends(get_db),
) -> Done:
    package = packages_service.open_for(db, package_id, person.id)
    item = packages_service.find_item(db, item_id)
    if package is None or item is None or item.package_id != package.id:
        raise HTTPException(status_code=404, detail="موردی پیدا نشد")
    return _deliver(lambda ctx, chat: _send_item(ctx, item, chat), db, person)


@router.get("/classes", response_model=list[ClassOption], operation_id="me_classes")
def class_options(
    _: Person = Depends(current_person), db: Session = Depends(get_db)
) -> list[ClassOption]:
    return [
        ClassOption(id=c.id, title=c.title)
        for c in classes_service.list_class_types(db, only_active=True)
    ]


@router.post("/course-request", response_model=Done, operation_id="me_course_request")
def course_request(
    body: CourseRequest, person: Person = Depends(current_person), db: Session = Depends(get_db)
) -> Done:
    title = None
    if body.class_type_id is not None:
        try:
            class_type = classes_service.get(db, body.class_type_id)
        except NotFoundError:
            class_type = None
        if class_type is None or not class_type.active:
            raise HTTPException(status_code=404, detail="کلاس پیدا نشد")
        title = class_type.title
    try:
        crm_service.request_course(db, person, title, body.note)
    except DomainError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Done(message="درخواستت برای مربی ثبت شد؛ به‌زودی باهات هماهنگ می‌کند.")


# --- delivery through the bot ---


def _deliver(send, db: Session, person: Person) -> Done:
    from app.bots.common.client import build_client
    from app.bots.common.context import make_context

    identity = next(
        (i for i in person.identities if i.platform == Platform.TELEGRAM), None
    )
    client = build_client(Platform.TELEGRAM) if identity else None
    if identity is None or client is None:
        raise HTTPException(
            status_code=409, detail="برای دریافت فایل، اول ربات تلگرام را استارت کن."
        )
    try:
        send(make_context(client), identity.platform_user_id)
    finally:
        client.close()
    return Done(message="فایل در چت تلگرامت ارسال شد.")


def _send_program(ctx, assignment, chat_id: object) -> None:
    from app.bots.common import client_flow, formatting

    client_flow._deliver_program(
        ctx, assignment, chat_id, formatting.format_program_caption(assignment)
    )


def _send_item(ctx, item, chat_id: object) -> None:
    from app.bots.common import client_flow

    client_flow._deliver_item(ctx, item, chat_id)
