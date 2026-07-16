"""Web-layer helpers: template engine and login-redirect dependencies."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request
from fastapi.templating import Jinja2Templates

from app.api.deps import DbDep, get_current_person_optional
from app.core.jalali import format_jalali
from app.models import Person, Role
from app.services import attendance as attendance_service
from app.services import payments as payments_service
from app.services import plans as plans_service


class LoginRedirect(Exception):
    """Raised by web dependencies when the visitor must log in first."""

    def __init__(self, target: str):
        self.target = target


def _build_templates() -> Jinja2Templates:
    templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
    env = templates.env
    env.filters["jdate"] = format_jalali
    env.filters["toman"] = lambda amount: f"{amount:,}"
    env.globals["attendance_label"] = attendance_service.status_label
    env.globals["payment_label"] = payments_service.kind_label
    env.globals["plan_label"] = plans_service.type_label
    return templates


templates = _build_templates()


def require_admin_web(request: Request, db: DbDep) -> Person:
    person = get_current_person_optional(request, db)
    if person is None or person.role != Role.ADMIN:
        raise LoginRedirect("/admin/login")
    return person


def require_person_web(request: Request, db: DbDep) -> Person:
    person = get_current_person_optional(request, db)
    if person is None:
        raise LoginRedirect("/login")
    return person


AdminWeb = Annotated[Person, Depends(require_admin_web)]
PersonWeb = Annotated[Person, Depends(require_person_web)]
