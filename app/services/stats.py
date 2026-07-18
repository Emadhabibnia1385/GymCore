"""Dashboard statistics for the admin panel."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Course,
    CourseStatus,
    Payment,
    Person,
    Role,
)


def dashboard(db: Session) -> dict:
    def count(stmt) -> int:
        return db.scalar(stmt) or 0

    return {
        "clients": count(
            select(func.count(Person.id)).where(
                Person.role == Role.CLIENT, Person.is_active.is_(True)
            )
        ),
        "active_courses": count(
            select(func.count(Course.id)).where(Course.status == CourseStatus.ACTIVE)
        ),
        "total_payments": count(select(func.coalesce(func.sum(Payment.amount), 0))),
    }
