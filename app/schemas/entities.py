"""Request/response schemas for the REST API (/api/v1)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.models import (
    AttendanceStatus,
    CourseStatus,
    PaymentKind,
    Platform,
    PlanType,
    RequestStatus,
    Role,
)
from app.schemas.common import ORMModel


# --- Auth ---


class LoginIn(BaseModel):
    phone: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


# --- Persons ---


class ChannelIdentityOut(ORMModel):
    id: int
    platform: Platform
    platform_user_id: str


class PersonOut(ORMModel):
    id: int
    name: str
    phone: str | None
    role: Role
    is_active: bool
    note: str | None
    created_at: datetime


class PersonDetailOut(PersonOut):
    identities: list[ChannelIdentityOut] = []


class PersonCreateIn(BaseModel):
    name: str
    phone: str | None = None
    role: Role = Role.CLIENT
    note: str | None = None


class PersonUpdateIn(BaseModel):
    name: str | None = None
    phone: str | None = None
    role: Role | None = None
    note: str | None = None
    is_active: bool | None = None


class SetPasswordIn(BaseModel):
    password: str = Field(min_length=6)


# --- Class types ---


class ClassTypeOut(ORMModel):
    id: int
    title: str
    description: str | None
    active: bool
    sort_order: int


class ClassTypeCreateIn(BaseModel):
    title: str
    description: str | None = None
    sort_order: int = 0


class ClassTypeUpdateIn(BaseModel):
    title: str | None = None
    description: str | None = None
    active: bool | None = None
    sort_order: int | None = None


# --- Courses ---


class CourseOut(ORMModel):
    id: int
    client_id: int
    class_type_id: int
    sessions_total: int
    tuition: int
    gym_fee: int
    start_date: date
    status: CourseStatus
    note: str | None
    created_at: datetime
    # Computed fields, filled by the router from the service layer.
    remaining_sessions: int = 0
    client_name: str = ""
    class_title: str = ""


class CourseCreateIn(BaseModel):
    client_id: int
    class_type_id: int
    sessions_total: int = Field(ge=1)
    tuition: int = Field(ge=0, default=0)
    gym_fee: int = Field(ge=0, default=0)
    start_date: date
    note: str | None = None


class CourseStatusIn(BaseModel):
    status: CourseStatus


# --- Attendance ---


class AttendanceOut(ORMModel):
    id: int
    course_id: int
    session_date: date
    status: AttendanceStatus
    note: str | None
    created_at: datetime


class AttendanceCreateIn(BaseModel):
    course_id: int
    session_date: date
    status: AttendanceStatus
    note: str | None = None


# --- Payments ---


class PaymentOut(ORMModel):
    id: int
    person_id: int
    course_id: int | None
    amount: int
    kind: PaymentKind
    method: str | None
    paid_at: date
    note: str | None
    created_at: datetime


class PaymentCreateIn(BaseModel):
    person_id: int
    amount: int
    kind: PaymentKind = PaymentKind.TUITION
    paid_at: date
    course_id: int | None = None
    method: str | None = None
    note: str | None = None


# --- Plans ---


class PlanOut(ORMModel):
    id: int
    person_id: int
    plan_type: PlanType
    title: str
    description: str | None
    original_filename: str | None
    active: bool
    created_at: datetime
    has_file: bool = False


# --- Requests ---


class ClassRequestOut(ORMModel):
    id: int
    person_id: int
    class_type_id: int
    note: str | None
    status: RequestStatus
    created_at: datetime
    person_name: str = ""
    class_title: str = ""


class PlanRequestOut(ORMModel):
    id: int
    person_id: int
    plan_type: PlanType
    note: str | None
    status: RequestStatus
    created_at: datetime
    person_name: str = ""


# --- Settings / stats ---


class SettingsOut(BaseModel):
    values: dict[str, str]


class SettingsIn(BaseModel):
    values: dict[str, str]
