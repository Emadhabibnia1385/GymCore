"""The web panel's API: Telegram sign-in, and the dashboards for coach and student.

Thin on purpose — every number comes from the same services the bots use, so the
panel and the bot can never disagree. Signed-in state is an httpOnly cookie set at
login (services/web_auth.py); admin rights are the bot's own rule
(`services/auth.is_admin`) evaluated live for the signed-in Telegram account.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.web_deps import COOKIE, current_session, require_admin
from app.core import clock
from app.core.config import get_settings
from app.core.exceptions import AuthError, ConflictError, ValidationError
from app.core.jalali import JALALI_MONTHS, format_jalali
from app.db.session import get_db
from app.models import ChannelIdentity, Person, Platform, WebSession
from app.models.setting import KEY_WEB_REGISTRATION
from app.services import crm as crm_service
from app.services import finance as finance_service
from app.services import payments as payments_service
from app.services import schedule as schedule_service
from app.services import settings as settings_service
from app.services import stats as stats_service
from app.services import web_accounts, web_auth, web_login

_COOKIE_MAX_AGE = 400 * 24 * 3600  # the longest a browser keeps a cookie; the server decides

router = APIRouter(prefix="/api", tags=["web"])


# --- schemas ---


class LoginConfig(BaseModel):
    bot_username: str
    dev_login: bool = False
    registration_open: bool = True


class Me(BaseModel):
    name: str
    role: str  # "admin" | "student"
    username: str | None = None


class PasswordLogin(BaseModel):
    username: str = Field(max_length=64)
    password: str = Field(max_length=200)


class Registration(PasswordLogin):
    name: str = Field(min_length=1, max_length=80)


class PasswordChange(BaseModel):
    old_password: str = Field(max_length=200)
    new_password: str = Field(max_length=200)


class Done(BaseModel):
    ok: bool = True
    message: str


class BotLoginStart(BaseModel):
    url: str
    secret: str
    expires_in: int


class BotLoginPoll(BaseModel):
    secret: str = Field(max_length=100)


class BotLoginState(BaseModel):
    state: str  # pending | approved | denied | expired
    me: Me | None = None


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


# --- auth ---


@router.get("/auth/config", response_model=LoginConfig, operation_id="auth_config")
def login_config(db: Session = Depends(get_db)) -> LoginConfig:
    settings = get_settings()
    return LoginConfig(
        bot_username=settings.telegram_bot_username,
        dev_login=settings.web_dev_login,
        registration_open=settings_service.get_bool(db, KEY_WEB_REGISTRATION, True),
    )


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
    return _open_session(db, person, fields["id"], request, response)


@router.post("/auth/dev", response_model=Me, operation_id="auth_dev", include_in_schema=False)
def login_dev(
    request: Request, response: Response, student: bool = False, db: Session = Depends(get_db)
) -> Me:
    """Local development only (WEB_DEV_LOGIN=true): sign in as the first owner, or
    with `?student=true` as the first student the bot knows."""
    owners = get_settings().telegram_owner_id_list
    if not get_settings().web_dev_login or not owners:
        raise HTTPException(status_code=404, detail="یافت نشد")
    if student:
        identity = db.scalar(
            select(ChannelIdentity)
            .where(
                ChannelIdentity.platform == Platform.TELEGRAM,
                ChannelIdentity.platform_user_id.notin_([str(o) for o in owners]),
            )
            .order_by(ChannelIdentity.id)
        )
        if identity is None:
            raise HTTPException(status_code=404, detail="شاگردی برای ورود آزمایشی نیست")
        user_id = identity.platform_user_id
        person = db.get(Person, identity.person_id)
    else:
        user_id = str(owners[0])
        person = web_auth.person_for_login(db, {"id": user_id, "first_name": "مربی"})
    return _open_session(db, person, user_id, request, response)


def _open_session(
    db: Session, person: Person, user_id: str | None, request: Request, response: Response
) -> Me:
    token = web_auth.start_session(db, person, user_id, request.headers.get("user-agent"))
    response.set_cookie(
        COOKIE, token, max_age=_COOKIE_MAX_AGE, httponly=True, samesite="lax",
        secure=get_settings().web_cookie_secure, path="/",
    )
    return _me(db, person, user_id)


def _client(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/auth/bot-login", response_model=BotLoginStart, operation_id="auth_bot_login")
def bot_login_start(request: Request, db: Session = Depends(get_db)) -> BotLoginStart:
    """Begin «log in with the bot»: the person opens the link and approves inside Telegram."""
    client = _client(request)
    if web_accounts.bot_logins.blocked(client):
        raise HTTPException(status_code=429, detail=web_accounts.THROTTLED)
    web_accounts.bot_logins.hit(client)
    token, secret = web_login.start(db, request.headers.get("user-agent"), client)
    bot = get_settings().telegram_bot_username
    return BotLoginStart(
        url=f"https://t.me/{bot}?start={web_login.START_PREFIX}{token}",
        secret=secret,
        expires_in=int(web_login.TTL.total_seconds()),
    )


@router.post(
    "/auth/bot-login/status", response_model=BotLoginState, operation_id="auth_bot_login_status"
)
def bot_login_status(
    body: BotLoginPoll, request: Request, response: Response, db: Session = Depends(get_db)
) -> BotLoginState:
    """The browser polls with its secret; once approved it gets its session, exactly once."""
    state, found = web_login.claim(db, body.secret)
    if state != "approved" or found is None:
        return BotLoginState(state=state)
    person = db.get(Person, found.person_id)
    if person is None or not person.is_active:
        return BotLoginState(state="denied")
    me = _open_session(db, person, found.telegram_user_id, request, response)
    return BotLoginState(state="approved", me=me)


@router.post("/auth/password", response_model=Me, operation_id="auth_password")
def login_password(
    body: PasswordLogin, request: Request, response: Response, db: Session = Depends(get_db)
) -> Me:
    try:
        person = web_accounts.authenticate(db, body.username, body.password, _client(request))
    except web_accounts.Throttled as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return _open_session(db, person, None, request, response)


@router.post("/auth/register", response_model=Me, operation_id="auth_register")
def register(
    body: Registration, request: Request, response: Response, db: Session = Depends(get_db)
) -> Me:
    if not settings_service.get_bool(db, KEY_WEB_REGISTRATION, True):
        raise HTTPException(status_code=403, detail="ثبت‌نام در پنل وب فعلاً بسته است")
    try:
        person = web_accounts.register(
            db, body.name, body.username, body.password, _client(request)
        )
    except web_accounts.Throttled as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    # The coach sees the new student on today's follow-ups, with everything else he chases.
    crm_service.add_follow_up(
        db, clock.today(), person_id=person.id, note="ثبت‌نام تازه از پنل وب", created_by="web"
    )
    return _open_session(db, person, None, request, response)


@router.post("/auth/password/change", response_model=Done, operation_id="auth_password_change")
def change_password(
    body: PasswordChange,
    session: WebSession = Depends(current_session),
    db: Session = Depends(get_db),
) -> Done:
    try:
        web_accounts.change_password(db, session.person_id, body.old_password, body.new_password)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except AuthError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return Done(message="گذرواژه عوض شد.")


@router.post("/auth/password/set", response_model=Me, operation_id="auth_password_set")
def set_password(
    body: PasswordLogin,
    session: WebSession = Depends(current_session),
    db: Session = Depends(get_db),
) -> Me:
    """Someone who signed in with Telegram adds a username and password of their own."""
    if web_accounts.username_of(db, session.person_id) is not None:
        raise HTTPException(status_code=409, detail="برای این حساب قبلاً گذرواژه تعریف شده")
    try:
        web_accounts.set_credentials(db, session.person_id, body.username, body.password)
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _me(db, db.get(Person, session.person_id), session.telegram_user_id)


@router.get("/auth/me", response_model=Me, operation_id="auth_me")
def me(session: WebSession = Depends(current_session), db: Session = Depends(get_db)) -> Me:
    return _me(db, db.get(Person, session.person_id), session.telegram_user_id)


@router.post("/auth/logout", operation_id="auth_logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict:
    web_auth.end_session(db, request.cookies.get(COOKIE))
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


def _me(db: Session, person: Person, telegram_user_id: str | None) -> Me:
    admin = web_auth.is_admin(db, person.id, telegram_user_id)
    return Me(
        name=person.name,
        role="admin" if admin else "student",
        username=web_accounts.username_of(db, person.id),
    )


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
