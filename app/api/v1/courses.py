"""Course + attendance endpoints.

Clients may read their own courses; admins manage everything.
Attendance is append-only: there is no update/delete route by design.
"""

from fastapi import APIRouter, HTTPException

from app.api.deps import AdminPerson, CurrentPerson, DbDep
from app.models import Course, CourseStatus, Role
from app.schemas.entities import (
    AttendanceCreateIn,
    AttendanceOut,
    CourseCreateIn,
    CourseOut,
    CourseStatusIn,
)
from app.services import attendance as attendance_service
from app.services import courses as courses_service

router = APIRouter(prefix="/courses", tags=["courses"])


def _to_out(db: DbDep, course: Course) -> CourseOut:
    out = CourseOut.model_validate(course)
    out.remaining_sessions = courses_service.remaining_sessions(db, course)
    out.client_name = course.client.name
    out.class_title = course.class_type.title
    return out


@router.get("", response_model=list[CourseOut])
def list_courses(
    db: DbDep,
    person: CurrentPerson,
    client_id: int | None = None,
    status: CourseStatus | None = None,
) -> list[CourseOut]:
    # Non-admins can only see their own courses.
    if person.role != Role.ADMIN:
        client_id = person.id
    return [
        _to_out(db, c)
        for c in courses_service.list_courses(db, client_id=client_id, status=status)
    ]


@router.post("", response_model=CourseOut, status_code=201)
def create_course(body: CourseCreateIn, db: DbDep, _: AdminPerson) -> CourseOut:
    course = courses_service.create(
        db,
        client_id=body.client_id,
        class_type_id=body.class_type_id,
        sessions_total=body.sessions_total,
        tuition=body.tuition,
        gym_fee=body.gym_fee,
        start_date=body.start_date,
        note=body.note,
    )
    return _to_out(db, course)


@router.get("/{course_id}", response_model=CourseOut)
def get_course(course_id: int, db: DbDep, person: CurrentPerson) -> CourseOut:
    course = courses_service.get(db, course_id)
    if person.role != Role.ADMIN and course.client_id != person.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return _to_out(db, course)


@router.patch("/{course_id}/status", response_model=CourseOut)
def set_course_status(
    course_id: int, body: CourseStatusIn, db: DbDep, _: AdminPerson
) -> CourseOut:
    course = courses_service.set_status(db, course_id, body.status)
    return _to_out(db, course)


@router.get("/{course_id}/attendance", response_model=list[AttendanceOut])
def list_attendance(
    course_id: int, db: DbDep, person: CurrentPerson
) -> list[AttendanceOut]:
    course = courses_service.get(db, course_id)
    if person.role != Role.ADMIN and course.client_id != person.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return [
        AttendanceOut.model_validate(e)
        for e in attendance_service.list_for_course(db, course_id)
    ]


@router.post("/{course_id}/attendance", response_model=AttendanceOut, status_code=201)
def record_attendance(
    course_id: int, body: AttendanceCreateIn, db: DbDep, _: AdminPerson
) -> AttendanceOut:
    if body.course_id != course_id:
        raise HTTPException(status_code=400, detail="course_id mismatch")
    event = attendance_service.record(
        db,
        course_id=course_id,
        session_date=body.session_date,
        status=body.status,
        note=body.note,
    )
    return AttendanceOut.model_validate(event)
