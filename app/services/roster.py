"""The coach's student roster — one list of everyone, in the order the coach works it.

In-person students come first, fewest sessions left on top, so whoever needs a renewal
is at the top; then those whose course just ended (the ones to call); then everybody
without a course; online students (programs only) last. The in-bot list (admin/
students.py) predates this and orders the same way.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import CourseStatus, Person, Role, StudentType
from app.services import courses as courses_service
from app.services import packages as packages_service
from app.services import persons as persons_service
from app.services import plans as plans_service


@dataclass(frozen=True)
class RosterRow:
    person: Person
    # "active" (has a running course), "ended", "none", or "online"
    state: str
    remaining: int | None  # sessions left on the active course
    programs: int
    packages: int


def list_students(
    db: Session, kind: StudentType | None = None, query: str | None = None
) -> list[RosterRow]:
    stmt = persons_service.search_stmt(Role.CLIENT, query or None, kind)
    rows: list[tuple[tuple[int, int], RosterRow]] = []
    for person in db.scalars(stmt):
        programs = len(plans_service.list_assignments(db, person_id=person.id))
        packages = len(packages_service.list_for_person(db, person.id))
        if person.student_type == StudentType.ONLINE:
            rows.append(((3, 0), RosterRow(person, "online", None, programs, packages)))
            continue
        active = courses_service.active_course(db, person.id)
        if active is not None:
            left = courses_service.remaining_sessions(db, active)
            rows.append(((0, left), RosterRow(person, "active", left, programs, packages)))
        elif db.scalar(courses_service.list_stmt(person.id, CourseStatus.FINISHED).limit(1)):
            rows.append(((1, 0), RosterRow(person, "ended", None, programs, packages)))
        else:
            rows.append(((2, 0), RosterRow(person, "none", None, programs, packages)))
    rows.sort(key=lambda row: row[0])
    return [row for _, row in rows]


def counts(db: Session) -> dict[StudentType, int]:
    return persons_service.count_by_type(db)

