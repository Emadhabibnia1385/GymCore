"""Admin panel routes (server-rendered, Persian RTL).

Every route delegates to the service layer — no business logic here.
Mutations follow POST → redirect (PRG) with ?msg= / ?error= flash params.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import RedirectResponse

from app.api.deps import COOKIE_NAME, DbDep
from app.core.config import get_settings
from app.core.exceptions import AuthError
from app.models import CourseStatus, PaymentKind, PlanType, Role
from app.models.setting import KEY_CONTACT_TEXT, KEY_GYM_NAME, KEY_WELCOME_TEXT
from app.services import app_settings as settings_service
from app.services import attendance as attendance_service
from app.services import auth as auth_service
from app.services import classes as classes_service
from app.services import courses as courses_service
from app.services import payments as payments_service
from app.services import persons as persons_service
from app.services import plans as plans_service
from app.services import requests as requests_service
from app.services import stats as stats_service
from app.models import AttendanceStatus, RequestStatus
from app.web.deps import AdminWeb, templates

router = APIRouter(prefix="/admin", include_in_schema=False)


def _redirect(path: str, msg: str | None = None) -> RedirectResponse:
    url = f"{path}?msg={msg}" if msg else path
    return RedirectResponse(url, status_code=303)


# --- Auth ---


@router.get("/login")
def login_page(request: Request, db: DbDep):
    return templates.TemplateResponse(request, "admin/login.html")


@router.post("/login")
def login_submit(
    request: Request, db: DbDep, phone: str = Form(...), password: str = Form(...)
):
    person, token = auth_service.login(db, phone, password)
    if person.role != Role.ADMIN:
        raise AuthError("این حساب دسترسی مدیریت ندارد")
    response = _redirect("/admin")
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=get_settings().access_token_expire_minutes * 60,
        httponly=True,
        samesite="lax",
        secure=get_settings().cookie_secure,
    )
    return response


@router.get("/logout")
def logout():
    response = _redirect("/admin/login")
    response.delete_cookie(COOKIE_NAME)
    return response


# --- Dashboard ---


@router.get("")
def dashboard(request: Request, db: DbDep, admin: AdminWeb):
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {
            "active": "dashboard",
            "stats": stats_service.dashboard(db),
            "pending_class": requests_service.list_class_requests(
                db, RequestStatus.PENDING
            ),
            "pending_plan": requests_service.list_plan_requests(
                db, RequestStatus.PENDING
            ),
        },
    )


# --- Students ---


@router.get("/students")
def students(request: Request, db: DbDep, admin: AdminWeb, search: str | None = None):
    return templates.TemplateResponse(
        request,
        "admin/students.html",
        {
            "active": "students",
            "persons": persons_service.list_persons(db, search=search),
            "search": search,
        },
    )


@router.post("/students")
def create_student(
    db: DbDep,
    admin: AdminWeb,
    name: str = Form(...),
    phone: str = Form(""),
    note: str = Form(""),
):
    person = persons_service.create(
        db, name=name, phone=phone or None, note=note or None
    )
    return _redirect(f"/admin/students/{person.id}", "شاگرد با موفقیت ثبت شد")


@router.get("/students/{person_id}")
def student_detail(request: Request, person_id: int, db: DbDep, admin: AdminWeb):
    person = persons_service.get(db, person_id)
    courses = [
        {"course": c, "remaining": courses_service.remaining_sessions(db, c)}
        for c in courses_service.list_courses(db, client_id=person_id)
    ]
    return templates.TemplateResponse(
        request,
        "admin/student_detail.html",
        {
            "active": "students",
            "person": person,
            "courses": courses,
            "plans": plans_service.list_plans(db, person_id=person_id),
            "payments": payments_service.list_payments(db, person_id=person_id),
        },
    )


@router.post("/students/{person_id}")
def update_student(
    person_id: int,
    db: DbDep,
    admin: AdminWeb,
    name: str = Form(...),
    phone: str = Form(""),
    role: Role = Form(Role.CLIENT),
    is_active: str = Form("true"),
    note: str = Form(""),
):
    persons_service.update(
        db,
        person_id,
        name=name,
        phone=phone,
        role=role,
        note=note,
        is_active=is_active == "true",
    )
    return _redirect(f"/admin/students/{person_id}", "تغییرات ذخیره شد")


@router.post("/students/{person_id}/password")
def set_student_password(
    person_id: int, db: DbDep, admin: AdminWeb, password: str = Form(...)
):
    persons_service.set_web_password(db, person_id, password)
    return _redirect(f"/admin/students/{person_id}", "رمز عبور تنظیم شد")


# --- Classes ---


@router.get("/classes")
def classes_page(request: Request, db: DbDep, admin: AdminWeb):
    return templates.TemplateResponse(
        request,
        "admin/classes.html",
        {"active": "classes", "class_types": classes_service.list_class_types(db)},
    )


@router.post("/classes")
def create_class(
    db: DbDep,
    admin: AdminWeb,
    title: str = Form(...),
    description: str = Form(""),
    sort_order: int = Form(0),
):
    classes_service.create(
        db, title=title, description=description or None, sort_order=sort_order
    )
    return _redirect("/admin/classes", "کلاس ثبت شد")


@router.post("/classes/{class_type_id}/toggle")
def toggle_class(class_type_id: int, db: DbDep, admin: AdminWeb):
    class_type = classes_service.get(db, class_type_id)
    classes_service.update(db, class_type_id, active=not class_type.active)
    return _redirect("/admin/classes", "وضعیت کلاس تغییر کرد")


# --- Courses ---


@router.get("/courses")
def courses_page(
    request: Request, db: DbDep, admin: AdminWeb, status: CourseStatus | None = None
):
    courses = [
        {"course": c, "remaining": courses_service.remaining_sessions(db, c)}
        for c in courses_service.list_courses(db, status=status)
    ]
    return templates.TemplateResponse(
        request,
        "admin/courses.html",
        {
            "active": "courses",
            "courses": courses,
            "clients": persons_service.list_persons(db, role=Role.CLIENT),
            "class_types": classes_service.list_class_types(db, only_active=True),
            "status_filter": status.value if status else None,
        },
    )


@router.post("/courses")
def create_course(
    db: DbDep,
    admin: AdminWeb,
    client_id: int = Form(...),
    class_type_id: int = Form(...),
    sessions_total: int = Form(...),
    tuition: int = Form(0),
    gym_fee: int = Form(0),
    start_date: date = Form(...),
):
    course = courses_service.create(
        db,
        client_id=client_id,
        class_type_id=class_type_id,
        sessions_total=sessions_total,
        tuition=tuition,
        gym_fee=gym_fee,
        start_date=start_date,
    )
    return _redirect(f"/admin/courses/{course.id}", "دوره ایجاد شد")


@router.get("/courses/{course_id}")
def course_detail(request: Request, course_id: int, db: DbDep, admin: AdminWeb):
    course = courses_service.get(db, course_id)
    return templates.TemplateResponse(
        request,
        "admin/course_detail.html",
        {
            "active": "courses",
            "course": course,
            "remaining": courses_service.remaining_sessions(db, course),
            "attendance": attendance_service.list_for_course(db, course_id),
            "payments": payments_service.list_payments(db, course_id=course_id),
            "total_paid": payments_service.total_paid(db, course_id),
            "today": date.today().isoformat(),
        },
    )


@router.post("/courses/{course_id}/status")
def course_status(
    course_id: int, db: DbDep, admin: AdminWeb, status: CourseStatus = Form(...)
):
    courses_service.set_status(db, course_id, status)
    return _redirect(f"/admin/courses/{course_id}", "وضعیت دوره تغییر کرد")


@router.post("/courses/{course_id}/attendance")
def course_attendance(
    course_id: int,
    db: DbDep,
    admin: AdminWeb,
    session_date: date = Form(...),
    status: AttendanceStatus = Form(...),
    note: str = Form(""),
):
    attendance_service.record(
        db,
        course_id=course_id,
        session_date=session_date,
        status=status,
        note=note or None,
    )
    return _redirect(f"/admin/courses/{course_id}", "جلسه ثبت شد")


@router.post("/courses/{course_id}/payments")
def course_payment(
    course_id: int,
    db: DbDep,
    admin: AdminWeb,
    amount: int = Form(...),
    kind: PaymentKind = Form(...),
    method: str = Form(""),
    paid_at: date = Form(...),
    note: str = Form(""),
):
    course = courses_service.get(db, course_id)
    payments_service.record(
        db,
        person_id=course.client_id,
        amount=amount,
        kind=kind,
        paid_at=paid_at,
        course_id=course_id,
        method=method or None,
        note=note or None,
    )
    return _redirect(f"/admin/courses/{course_id}", "پرداخت ثبت شد")


# --- Plans ---


@router.get("/plans")
def plans_page(request: Request, db: DbDep, admin: AdminWeb):
    return templates.TemplateResponse(
        request,
        "admin/plans.html",
        {
            "active": "plans",
            "plans": plans_service.list_plans(db),
            "clients": persons_service.list_persons(db, role=Role.CLIENT),
        },
    )


@router.post("/plans")
async def create_plan(
    db: DbDep,
    admin: AdminWeb,
    person_id: int = Form(...),
    plan_type: PlanType = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    file: UploadFile | None = File(None),
):
    stored_name = None
    original_filename = None
    if file is not None and file.filename:
        content = await file.read()
        stored_name = plans_service.save_attachment(file.filename, content)
        original_filename = file.filename
    plans_service.create(
        db,
        person_id=person_id,
        plan_type=plan_type,
        title=title,
        description=description or None,
        file_path=stored_name,
        original_filename=original_filename,
    )
    return _redirect("/admin/plans", "برنامه ثبت شد و به شاگرد اطلاع داده شد")


@router.post("/plans/{plan_id}/toggle")
def toggle_plan(plan_id: int, db: DbDep, admin: AdminWeb):
    plan = plans_service.get(db, plan_id)
    plans_service.set_active(db, plan_id, not plan.active)
    return _redirect("/admin/plans", "وضعیت برنامه تغییر کرد")


# --- Requests ---


@router.get("/requests")
def requests_page(request: Request, db: DbDep, admin: AdminWeb):
    return templates.TemplateResponse(
        request,
        "admin/requests.html",
        {
            "active": "requests",
            "class_requests": requests_service.list_class_requests(db),
            "plan_requests": requests_service.list_plan_requests(db),
        },
    )


@router.post("/requests/classes/{request_id}")
def decide_class_request(
    request_id: int, db: DbDep, admin: AdminWeb, decision: str = Form(...)
):
    requests_service.decide_class_request(db, request_id, decision == "approve")
    return _redirect("/admin/requests", "درخواست بررسی شد")


@router.post("/requests/plans/{request_id}")
def decide_plan_request(
    request_id: int, db: DbDep, admin: AdminWeb, decision: str = Form(...)
):
    requests_service.decide_plan_request(db, request_id, decision == "approve")
    return _redirect("/admin/requests", "سفارش بررسی شد")


# --- Settings ---


@router.get("/settings")
def settings_page(request: Request, db: DbDep, admin: AdminWeb):
    return templates.TemplateResponse(
        request,
        "admin/settings.html",
        {"active": "settings", "values": settings_service.get_all(db)},
    )


@router.post("/settings")
def save_settings(
    db: DbDep,
    admin: AdminWeb,
    gym_name: str = Form(""),
    welcome_text: str = Form(""),
    contact_text: str = Form(""),
):
    settings_service.set_value(db, KEY_GYM_NAME, gym_name)
    settings_service.set_value(db, KEY_WELCOME_TEXT, welcome_text)
    settings_service.set_value(db, KEY_CONTACT_TEXT, contact_text)
    return _redirect("/admin/settings", "تنظیمات ذخیره شد")
