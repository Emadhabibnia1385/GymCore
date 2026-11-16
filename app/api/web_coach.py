"""The coach's daily work on the web: attendance, payments, expenses and the money report.

Each route is a thin call into the same service the bot's button calls, so a rule
(attendance is append-only, payments are immutable and corrected by a negative row,
a session date has to sit near its course) holds identically on both. Service
errors become HTTP errors in one place (api/main.py).
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.web_deps import require_admin
from app.bots.common import grid
from app.copy import finance_texts as F
from app.core import clock
from app.core.exceptions import NotFoundError, ValidationError
from app.core.jalali import JALALI_MONTHS, format_jalali
from app.db.session import get_db
from app.models import AttendanceStatus, Course, ExpenseCategory, PaymentKind, WebSession
from app.services import attendance as attendance_service
from app.services import courses as courses_service
from app.services import finance as finance_service
from app.services import payments as payments_service
from app.services import roster as roster_service
from app.services import schedule as schedule_service

router = APIRouter(prefix="/api/admin", tags=["coach"], dependencies=[Depends(require_admin)])

_KIND_LABELS = {"TUITION": "شهریه", "GYM_FEE": "ورودی باشگاه", "OTHER": "سایر"}
_STATUS_CODES = [s for s in AttendanceStatus if s != AttendanceStatus.MOVED]


def _by(session: WebSession) -> str:
    return str(session.telegram_user_id or f"web:{session.person_id}")


# --- attendance ---


class DayRow(BaseModel):
    course_id: int
    student: str
    class_title: str
    time: str
    status: str | None
    label: str


class Day(BaseModel):
    iso: str
    label: str
    is_today: bool
    is_future: bool
    prev: str
    next: str
    rows: list[DayRow]


class AttendanceIn(BaseModel):
    course_id: int
    date: date
    status: AttendanceStatus
    note: str | None = Field(default=None, max_length=500)


class MoveIn(BaseModel):
    course_id: int
    date: date
    new_date: date


class Saved(BaseModel):
    ok: bool = True
    message: str


def _day_view(db: Session, day: date) -> Day:
    rows = []
    for course in roster_service.sessions_on(db, day):
        status = courses_service.effective_status_map(db, course.id).get(day)
        rows.append(
            DayRow(
                course_id=course.id,
                student=course.client.name,
                class_title=course.class_type.title,
                time=schedule_service.day_time(course, schedule_service.persian_weekday(day)),
                status=status.value if status else None,
                label=grid.outcome_label(status),
            )
        )
    today = clock.today()
    return Day(
        iso=day.isoformat(),
        label=f"{schedule_service.weekday_name(day)} {format_jalali(day)}",
        is_today=day == today,
        is_future=day > today,
        prev=(day - timedelta(days=1)).isoformat(),
        next=(day + timedelta(days=1)).isoformat(),
        rows=rows,
    )


@router.get("/attendance/day", response_model=Day, operation_id="attendance_day")
def attendance_day(
    day: date | None = Query(default=None, alias="date"), db: Session = Depends(get_db)
) -> Day:
    return _day_view(db, day or clock.today())


@router.post("/attendance", response_model=Saved, operation_id="attendance_record")
def record_attendance(
    body: AttendanceIn, session: WebSession = Depends(require_admin), db: Session = Depends(get_db)
) -> Saved:
    if body.status == AttendanceStatus.MOVED:
        raise ValidationError("برای جابه‌جایی جلسه از «جایگزین» استفاده کن")
    if body.date > clock.today():  # a stale tap can't record a session that hasn't happened
        raise ValidationError("این جلسه هنوز فرا نرسیده است؛ پس از رسیدن تاریخ ثبتش کن")
    attendance_service.record(
        db, body.course_id, body.date, body.status, note=body.note, created_by=_by(session)
    )
    return Saved(message="حضور و غیاب ثبت شد.")


@router.post("/attendance/move", response_model=Saved, operation_id="attendance_move")
def move_session(
    body: MoveIn, session: WebSession = Depends(require_admin), db: Session = Depends(get_db)
) -> Saved:
    attendance_service.move_session(
        db, body.course_id, body.date, body.new_date, created_by=_by(session)
    )
    return Saved(message=f"جلسه به {format_jalali(body.new_date)} منتقل شد.")


@router.get("/attendance/statuses", operation_id="attendance_statuses")
def attendance_statuses() -> list[dict]:
    """The outcomes the coach can pick, in the order of the bot's picker."""
    order = [*grid.PRIMARY_STATUSES, *grid.SECONDARY_STATUSES]
    return [{"value": s.value, "label": grid.PICKER_LABELS[s]} for s in order if s in _STATUS_CODES]


# --- payments ---


class PaymentIn(BaseModel):
    person_id: int
    amount: int = Field(description="Toman; negative corrects an earlier payment")
    kind: PaymentKind
    paid_at: date
    course_id: int | None = None
    note: str | None = Field(default=None, max_length=300)


class OwingRow(BaseModel):
    person_id: int
    course_id: int
    student: str
    class_title: str
    amount: int


@router.post("/payments", response_model=Saved, operation_id="payment_record")
def record_payment(
    body: PaymentIn, session: WebSession = Depends(require_admin), db: Session = Depends(get_db)
) -> Saved:
    if body.course_id is not None:
        course = db.get(Course, body.course_id)
        if course is None or course.client_id != body.person_id:
            raise NotFoundError("دوره‌ای برای این شاگرد پیدا نشد")
    payments_service.record(
        db, body.person_id, body.amount, body.kind, body.paid_at,
        course_id=body.course_id, note=body.note, created_by=_by(session),
    )
    return Saved(message="پرداخت ثبت شد.")


@router.get("/payments/owing", response_model=list[OwingRow], operation_id="payments_owing")
def payments_owing(db: Session = Depends(get_db)) -> list[OwingRow]:
    return [
        OwingRow(
            person_id=c.client_id, course_id=c.id, student=c.client.name,
            class_title=c.class_type.title, amount=amount,
        )
        for c, amount in payments_service.outstanding_courses(db)
    ]


@router.get("/payments/kinds", operation_id="payment_kinds")
def payment_kinds() -> list[dict]:
    return [{"value": k, "label": label} for k, label in _KIND_LABELS.items()]


# --- expenses and the monthly report ---


class ExpenseIn(BaseModel):
    amount: int = Field(description="Toman; negative corrects an earlier expense")
    category: ExpenseCategory
    spent_at: date
    note: str | None = Field(default=None, max_length=300)


class Line(BaseModel):
    key: str
    label: str
    amount: int


class MonthView(BaseModel):
    jy: int
    jm: int
    label: str
    income: int
    income_by_kind: list[Line]
    payments: int
    corrections: int
    expenses: int
    expenses_by_category: list[Line]
    net: int
    prev: tuple[int, int]
    next: tuple[int, int] | None


class YearRow(BaseModel):
    jm: int
    label: str
    income: int
    expenses: int
    net: int


class YearView(BaseModel):
    jy: int
    rows: list[YearRow]
    income: int
    expenses: int
    net: int


class ExpenseRow(BaseModel):
    id: int
    amount: int
    date: str
    category: str
    category_label: str
    note: str | None


@router.get("/finance/month", response_model=MonthView, operation_id="finance_month")
def finance_month(
    jy: int | None = None, jm: int | None = None, db: Session = Depends(get_db)
) -> MonthView:
    now = finance_service.current_month()
    jy, jm = (jy, jm) if jy and jm and 1 <= jm <= 12 and (jy, jm) <= now else now
    report = finance_service.month_report(db, jy, jm)
    following = finance_service.shift_month(jy, jm, 1)
    return MonthView(
        jy=jy, jm=jm, label=f"{JALALI_MONTHS[jm - 1]} {jy}",
        income=report.income,
        income_by_kind=[
            Line(key=k.value, label=_KIND_LABELS[k.value], amount=v)
            for k, v in report.income_by_kind.items() if v
        ],
        payments=report.payment_count, corrections=report.correction_count,
        expenses=report.expenses,
        expenses_by_category=[
            Line(key=k.value, label=F.CATEGORY_LABELS[k.value], amount=v)
            for k, v in report.expenses_by_category.items() if v
        ],
        net=report.net,
        prev=finance_service.shift_month(jy, jm, -1),
        next=following if following <= now else None,
    )


@router.get("/finance/year", response_model=YearView, operation_id="finance_year")
def finance_year(jy: int | None = None, db: Session = Depends(get_db)) -> YearView:
    jy = jy or finance_service.current_month()[0]
    rows = finance_service.year_overview(db, jy)
    return YearView(
        jy=jy,
        rows=[
            YearRow(
                jm=r.jm, label=JALALI_MONTHS[r.jm - 1], income=r.income,
                expenses=r.expenses, net=r.net,
            )
            for r in rows
        ],
        income=sum(r.income for r in rows),
        expenses=sum(r.expenses for r in rows),
        net=sum(r.net for r in rows),
    )


@router.get("/finance/expenses", response_model=list[ExpenseRow], operation_id="finance_expenses")
def finance_expenses(jy: int, jm: int, db: Session = Depends(get_db)) -> list[ExpenseRow]:
    if not 1 <= jm <= 12:
        raise ValidationError("ماه نامعتبر است")
    return [
        ExpenseRow(
            id=e.id, amount=e.amount, date=format_jalali(e.spent_at), category=e.category.value,
            category_label=F.CATEGORY_LABELS[e.category.value], note=e.note,
        )
        for e in finance_service.list_expenses(db, jy, jm)
    ]


@router.post("/expenses", response_model=Saved, operation_id="expense_record")
def record_expense(
    body: ExpenseIn, session: WebSession = Depends(require_admin), db: Session = Depends(get_db)
) -> Saved:
    finance_service.record_expense(
        db, body.amount, body.category, body.spent_at, note=body.note, created_by=_by(session)
    )
    return Saved(message="هزینه ثبت شد.")


@router.get("/finance/categories", operation_id="finance_categories")
def finance_categories() -> list[dict]:
    return [{"value": k, "label": label} for k, label in F.CATEGORY_LABELS.items()]
