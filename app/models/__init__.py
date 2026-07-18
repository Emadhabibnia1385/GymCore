"""Import every model so Base.metadata knows all tables."""

from app.models.attendance import AttendanceEvent
from app.models.class_type import ClassType
from app.models.course import Course
from app.models.enums import (
    SESSION_CONSUMING_STATUSES,
    AttendanceStatus,
    CourseStatus,
    PaymentKind,
    PlanType,
    Platform,
    ReminderKind,
    Role,
)
from app.models.payment import Payment
from app.models.person import ChannelIdentity, Person
from app.models.plan import Plan
from app.models.reminder import ReminderLog
from app.models.setting import Setting

__all__ = [
    "AttendanceEvent",
    "AttendanceStatus",
    "ChannelIdentity",
    "ClassType",
    "Course",
    "CourseStatus",
    "Payment",
    "PaymentKind",
    "Person",
    "Plan",
    "PlanType",
    "Platform",
    "ReminderKind",
    "ReminderLog",
    "Role",
    "SESSION_CONSUMING_STATUSES",
    "Setting",
]
