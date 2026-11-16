"""The web panel's API: Telegram sign-in, and the dashboards for coach and student.

Thin on purpose — every number comes from the same services the bots use, so the
panel and the bot can never disagree. Signed-in state is an httpOnly cookie set at
login (services/web_auth.py); admin rights are the bot's own rule
(`services/auth.is_admin`) evaluated live for the signed-in Telegram account.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core import clock
from app.core.config import get_settings
from app.core.exceptions import AuthError
from app.core.jalali import JALALI_MONTHS, format_jalali
from app.db.session import get_db
from app.models import Person, Platform, WebSession
from app.services import auth as auth_service
from app.services import crm as crm_service
from app.services import finance as finance_service
from app.services import payments as payments_service
from app.services import schedule as schedule_service
from app.services import stats as stats_service
from app.services import web_auth

COOKIE = "gc_session"
_COOKIE_MAX_AGE = 400 * 24 * 3600  # the longest a browser keeps a cookie; the server decides

router = APIRouter(prefix="/api", tags=["web"])


# --- schemas ---


class LoginConfig(BaseModel):
    bot_username: str


class Me(BaseModel):
    name: str
    role: str  # "admin" | "student"


class Totals(BaseModel):
    clients: int
    active_courses: int
    programs: int


class MonthFigures(BaseModel):
    label: str
    income: int
    expenses: int
    net: int
    payments: int


class MonthPoint(BaseModel):
    month: int
    label: str
    income: int
    expenses: int
    net: int


class OwingRow(BaseModel):
    student: str
    class_title: str
    amount: int


class Owing(BaseModel):
    count: int
    total: int
    top: list[OwingRow]


class ClassToday(BaseModel):
    time: str
    student: str
    class_title: str


class FollowUps(BaseModel):
    due: int
    renewals: int
    open_leads: int


class AdminDashboard(BaseModel):
    totals: Totals
    month: MonthFigures
    year_label: str
    months: list[MonthPoint]
    owing: Owing
    today_label: str
    today: list[ClassToday]
    follow_ups: FollowUps


# --- session plumbing ---


def current_session(request: Request, db: Session = Depends(get_db)) -> WebSession:
    session = web_auth.resolve_session(db, request.cookies.get(COOKIE))
    if session is None:
        raise HTTPException(status_code=401, detail="وارد نشده‌ای")
    return session


def require_admin(
    session: WebSession = Depends(current_session), db: Session = Depends(get_db)
) -> WebSession:
    if not auth_service.is_admin(db, Platform.TELEGRAM, session.telegram_user_id):
        raise HTTPException(status_code=403, detail="دسترسی به این بخش مجاز نیست")
    return session


# --- auth ---


@router.get("/auth/config", response_model=LoginConfig, operation_id="auth_config")
def login_config() -> LoginConfig:
    return LoginConfig(bot_username=get_settings().telegram_bot_username)


@router.post("/auth/telegram", response_model=Me, operation_id="auth_telegram")
def login_telegram(
    payload: dict, request: Request, response: Response, db: Session = Depends(get_db)
) -> Me:
    settings = get_settings()
    try:
        fields = web_auth.verify_telegram_login(payload, settings.telegram_bot_token)
        person = web_auth.person_for_login(db, fields)
    except AuthError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    token = web_auth.start_session(
        db, person, fields["id"], request.headers.get("user-agent")
    )
    response.set_cookie(
        COOKIE, token, max_age=_COOKIE_MAX_AGE, httponly=True, samesite="lax",
        secure=settings.web_cookie_secure, path="/",
    )
    return _me(db, person, fields["id"])


@router.get("/auth/me", response_model=Me, operation_id="auth_me")
def me(session: WebSession = Depends(current_session), db: Session = Depends(get_db)) -> Me:
    return _me(db, db.get(Person, session.person_id), session.telegram_user_id)


@router.post("/auth/logout", operation_id="auth_logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    web_auth.end_session(db, request.cookies.get(COOKIE))
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


def _me(db: Session, person: Person, telegram_user_id: str) -> Me:
    admin = auth_service.is_admin(db, Platform.TELEGRAM, telegram_user_id)
    return Me(name=person.name, role="admin" if admin else "student")


# --- admin dashboard ---


@router.get(
    "/admin/dashboard", response_model=AdminDashboard, operation_id="admin_dashboard",
    dependencies=[Depends(require_admin)],
)
def admin_dashboard(db: Session = Depends(get_db)) -> AdminDashboard:
    today = clock.today()
    jy, jm = finance_service.month_of(today)
    report = finance_service.month_report(db, jy, jm)
    year = finance_service.year_overview(db, jy)
    owing = payments_service.outstanding_courses(db)
    weekday = schedule_service.persian_weekday(today)
    classes = schedule_service.weekly_timetable(db).get(weekday, [])
    totals = stats_service.dashboard(db)
    return AdminDashboard(
        totals=Totals(
            clients=totals["clients"], active_courses=totals["active_courses"],
            programs=totals["programs"],
        ),
        month=MonthFigures(
            label=f"{JALALI_MONTHS[jm - 1]} {jy}", income=report.income,
            expenses=report.expenses, net=report.net, payments=report.payment_count,
        ),
        year_label=str(jy),
        months=[
            MonthPoint(
                month=row.jm, label=JALALI_MONTHS[row.jm - 1], income=row.income,
                expenses=row.expenses, net=row.net,
            )
            for row in year
        ],
        owing=Owing(
            count=len(owing), total=sum(amount for _, amount in owing),
            top=[
                OwingRow(student=c.client.name, class_title=c.class_type.title, amount=amount)
                for c, amount in owing[:5]
            ],
        ),
        today_label=f"{schedule_service.weekday_name(today)} {format_jalali(today)}",
        today=[
            ClassToday(
                time=entry.time, student=entry.course.client.name,
                class_title=entry.course.class_type.title,
            )
            for entry in classes
        ],
        follow_ups=FollowUps(
            due=crm_service.count_due(db),
            renewals=len(crm_service.renewal_candidates(db)),
            open_leads=crm_service.count_open_leads(db),
        ),
    )
