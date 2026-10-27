"""Import every model so Base.metadata knows all tables.

Import order matters only in that each module's dependencies are imported first;
SQLAlchemy resolves string-based relationships once all classes are loaded.
"""

from app.models.attendance import AttendanceEvent
from app.models.channel_identity import ChannelIdentity
from app.models.class_type import ClassType
from app.models.contact_link import ContactLink
from app.models.course import Course
from app.models.crm import OPEN_LEAD_STATUSES, FollowUp, Lead, LeadSource, LeadStatus, PersonNote
from app.models.enums import (
    SESSION_CONSUMING_STATUSES,
    AttendanceStatus,
    CourseStatus,
    NotificationKind,
    NotificationStatus,
    PaymentKind,
    Platform,
    Role,
    StudentType,
)
from app.models.notification import Notification
from app.models.payment import Payment
from app.models.person import Person
from app.models.plan_assignment import PlanAssignment
from app.models.plan_type import PlanType
from app.models.setting import Setting

__all__ = [
    "OPEN_LEAD_STATUSES",
    "SESSION_CONSUMING_STATUSES",
    "AttendanceEvent",
    "AttendanceStatus",
    "ChannelIdentity",
    "ClassType",
    "ContactLink",
    "Course",
    "CourseStatus",
    "FollowUp",
    "Lead",
    "LeadSource",
    "LeadStatus",
    "Notification",
    "NotificationKind",
    "NotificationStatus",
    "Payment",
    "PaymentKind",
    "Person",
    "PersonNote",
    "PlanAssignment",
    "PlanType",
    "Platform",
    "Role",
    "Setting",
    "StudentType",
]
