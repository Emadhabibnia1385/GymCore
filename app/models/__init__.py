"""Import every model so Base.metadata knows all tables.

Import order matters only in that each module's dependencies are imported first;
SQLAlchemy resolves string-based relationships once all classes are loaded.
"""

from app.models.attendance import AttendanceEvent
from app.models.channel_identity import ChannelIdentity
from app.models.class_type import ClassType
from app.models.contact_link import ContactLink
from app.models.course import Course
from app.models.enums import (
    SESSION_CONSUMING_STATUSES,
    AttendanceStatus,
    CourseStatus,
    NotificationKind,
    NotificationStatus,
    PaymentKind,
    Platform,
    ReminderKind,
    Role,
)
from app.models.notification import Notification
from app.models.payment import Payment
from app.models.person import Person
from app.models.plan_assignment import PlanAssignment
from app.models.plan_type import PlanType
from app.models.reminder import ReminderLog
from app.models.setting import Setting

__all__ = [
    "SESSION_CONSUMING_STATUSES",
    "AttendanceEvent",
    "AttendanceStatus",
    "ChannelIdentity",
    "ClassType",
    "ContactLink",
    "Course",
    "CourseStatus",
    "Notification",
    "NotificationKind",
    "NotificationStatus",
    "Payment",
    "PaymentKind",
    "Person",
    "PlanAssignment",
    "PlanType",
    "Platform",
    "ReminderKind",
    "ReminderLog",
    "Role",
    "Setting",
]
