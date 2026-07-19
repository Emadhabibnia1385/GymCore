"""Domain enumerations (stored as strings for readability in the DB)."""

import enum


class Role(str, enum.Enum):
    CLIENT = "CLIENT"
    COACH = "COACH"
    ADMIN = "ADMIN"


class Platform(str, enum.Enum):
    TELEGRAM = "TELEGRAM"
    BALE = "BALE"
    # Retained only for backward compatibility with the v1 enum type; unused.
    WEB = "WEB"


class CourseStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    FINISHED = "FINISHED"
    PAUSED = "PAUSED"


class AttendanceStatus(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT_ALLOWED = "ABSENT_ALLOWED"
    ABSENT_UNAUTHORIZED = "ABSENT_UNAUTHORIZED"
    COACH_CANCELLED = "COACH_CANCELLED"
    HOLIDAY = "HOLIDAY"


# Statuses that consume one of the course's paid sessions.
# Business rule: a client "spends" a session by attending or by an
# unauthorized absence; excused absences, coach cancellations and holidays
# do not burn sessions.
SESSION_CONSUMING_STATUSES = frozenset(
    {AttendanceStatus.PRESENT, AttendanceStatus.ABSENT_UNAUTHORIZED}
)


class PaymentKind(str, enum.Enum):
    TUITION = "TUITION"
    GYM_FEE = "GYM_FEE"
    OTHER = "OTHER"


class ReminderKind(str, enum.Enum):
    """Automated reminders written to reminder_logs by the worker (v1, retained)."""

    LOW_SESSIONS = "LOW_SESSIONS"
    COURSE_INACTIVE = "COURSE_INACTIVE"


class NotificationKind(str, enum.Enum):
    """Categories for the unified notification system."""

    LOW_SESSIONS = "LOW_SESSIONS"
    COURSE_ENDING = "COURSE_ENDING"
    PAYMENT_REMINDER = "PAYMENT_REMINDER"
    NEW_PLAN = "NEW_PLAN"
    ATTENDANCE = "ATTENDANCE"
    MANUAL = "MANUAL"
    BROADCAST = "BROADCAST"


class NotificationStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
