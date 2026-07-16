"""Shared FastAPI dependencies: DB session and authentication.

Tokens are accepted from the `Authorization: Bearer` header (API/mobile)
or the `gymcore_token` HttpOnly cookie (web dashboard).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Person, Role
from app.services import auth as auth_service

COOKIE_NAME = "gymcore_token"

DbDep = Annotated[Session, Depends(get_db)]


def _extract_token(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header.removeprefix("Bearer ").strip()
    return request.cookies.get(COOKIE_NAME)


def get_current_person_optional(request: Request, db: DbDep) -> Person | None:
    token = _extract_token(request)
    if not token:
        return None
    return auth_service.resolve_token(db, token)


def get_current_person(request: Request, db: DbDep) -> Person:
    person = get_current_person_optional(request, db)
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return person


CurrentPerson = Annotated[Person, Depends(get_current_person)]


def require_admin(person: CurrentPerson) -> Person:
    if person.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return person


AdminPerson = Annotated[Person, Depends(require_admin)]
