"""Domain enumerations (stored as strings for readability in the DB)."""

import enum


class Role(str, enum.Enum):
    CLIENT = "CLIENT"
    COACH = "COACH"
    ADMIN = "ADMIN"


class Platform(str, enum.Enum):
    TELEGRAM = "TELEGRAM"
    BALE = "BALE"
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
# unauthorized absence; excused absences, coach cancellations and
# holidays do not burn sessions.
SESSION_CONSUMING_STATUSES = frozenset(
    {AttendanceStatus.PRESENT, AttendanceStatus.ABSENT_UNAUTHORIZED}
)


class PaymentKind(str, enum.Enum):
    TUITION = "TUITION"
    GYM_FEE = "GYM_FEE"
    OTHER = "OTHER"


class PlanType(str, enum.Enum):
    TRAINING = "TRAINING"
    NUTRITION = "NUTRITION"
    CUSTOM = "CUSTOM"


class ReminderKind(str, enum.Enum):
    """Automated reminders sent to clients by the background worker."""

    # Few paid sessions remain on an active course.
    LOW_SESSIONS = "LOW_SESSIONS"
    # No attendance recorded on an active course for a while.
    COURSE_INACTIVE = "COURSE_INACTIVE"
