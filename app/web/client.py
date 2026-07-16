"""Client dashboard routes: login + personal overview (courses, plans, payments)."""

from __future__ import annotations

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.api.deps import COOKIE_NAME, DbDep, get_current_person_optional
from app.core.config import get_settings
from app.models import Role
from app.models.setting import KEY_GYM_NAME
from app.services import app_settings as settings_service
from app.services import attendance as attendance_service
from app.services import auth as auth_service
from app.services import courses as courses_service
from app.services import payments as payments_service
from app.services import plans as plans_service
from app.web.deps import PersonWeb, templates

router = APIRouter(include_in_schema=False)


@router.get("/")
def home(request: Request, db: DbDep):
    person = get_current_person_optional(request, db)
    if person is None:
        return RedirectResponse("/login", status_code=303)
    if person.role == Role.ADMIN:
        return RedirectResponse("/admin", status_code=303)
    return RedirectResponse("/me", status_code=303)


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "client/login.html")


@router.post("/login")
def login_submit(db: DbDep, phone: str = Form(...), password: str = Form(...)):
    person, token = auth_service.login(db, phone, password)
    target = "/admin" if person.role == Role.ADMIN else "/me"
    response = RedirectResponse(target, status_code=303)
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
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response


@router.get("/me")
def me(request: Request, db: DbDep, person: PersonWeb):
    courses = [
        {
            "course": course,
            "remaining": courses_service.remaining_sessions(db, course),
            "attendance": attendance_service.list_for_course(db, course.id),
        }
        for course in courses_service.list_courses(db, client_id=person.id)
    ]
    return templates.TemplateResponse(
        request,
        "client/me.html",
        {
            "person": person,
            "gym_name": settings_service.get_value(db, KEY_GYM_NAME),
            "courses": courses,
            "plans": plans_service.list_plans(db, person_id=person.id, only_active=True),
            "payments": payments_service.list_payments(db, person_id=person.id),
        },
    )
