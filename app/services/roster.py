"""The coach's student roster — one list of everyone, in the order the coach works it.

In-person students come first, fewest sessions left on top, so whoever needs a renewal
is at the top; then those whose course just ended (the ones to call); then everybody
without a course; online students (programs only) last. The in-bot list (admin/
students.py) predates this and orders the same way.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.models import Course, CourseStatus, Person, Role, StudentType
from app.services import courses as courses_service
from app.services import packages as packages_service
from app.services import payments as payments_service
from app.services import persons as persons_service
from app.services import plans as plans_service
from app.services import schedule as schedule_service


@dataclass(frozen=True)
class RosterRow:
    person: Person
    # "active" (has a running course), "ended", "none", or "online"
    state: str
    remaining: int | None  # sessions left on the active course
    programs: int
    packages: int
    class_title: str | None = None  # the active course's class
    total: int | None = None  # sessions bought on the active course
    owing: int = 0  # what the student still owes across every course


def _owing(db: Session, person_id: int) -> int:
    return sum(
        payments_service.course_balance(db, course)["outstanding"]
        for course in db.scalars(courses_service.list_stmt(person_id))
    )


def list_students(
    db: Session, kind: StudentType | None = None, query: str | None = None
) -> list[RosterRow]:
    stmt = persons_service.search_stmt(Role.CLIENT, query or None, kind)
    rows: list[tuple[tuple[int, int], RosterRow]] = []
    for person in db.scalars(stmt):
        programs = len(plans_service.list_assignments(db, person_id=person.id))
        packages = len(packages_service.list_for_person(db, person.id))
        if person.student_type == StudentType.ONLINE:
            rows.append(((3, 0), RosterRow(
                person, "online", None, programs, packages, owing=_owing(db, person.id),
            )))
            continue
        active = courses_service.active_course(db, person.id)
        if active is not None:
            left = courses_service.remaining_sessions(db, active)
            rows.append(((0, left), RosterRow(
                person, "active", left, programs, packages,
                class_title=active.class_type.title, total=active.sessions_total,
                owing=_owing(db, person.id),
            )))
        elif db.scalar(courses_service.list_stmt(person.id, CourseStatus.FINISHED).limit(1)):
            rows.append(((1, 0), RosterRow(
                person, "ended", None, programs, packages, owing=_owing(db, person.id),
            )))
        else:
            rows.append(((2, 0), RosterRow(
                person, "none", None, programs, packages, owing=_owing(db, person.id),
            )))
    rows.sort(key=lambda row: row[0])
    return [row for _, row in rows]


def counts(db: Session) -> dict[StudentType, int]:
    return persons_service.count_by_type(db)



def sessions_on(db: Session, day: date) -> list[Course]:
    """Active courses with a session on `day`: the weekly pattern, plus any session
    rescheduled onto it, minus one moved away from it. By student name."""
    courses = [
        course
        for course in courses_service.list_courses(db, status=CourseStatus.ACTIVE)
        if day >= course.start_date
        and schedule_service.find_slot(schedule_service.build(db, course), day) is not None
    ]
    courses.sort(key=lambda c: c.client.name)
    return courses
