"""Shared plumbing for the web panel's routers: who is signed in, and who is the coach."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Person, WebSession
from app.services import web_auth

COOKIE = "gc_session"


def current_session(request: Request, db: Session = Depends(get_db)) -> WebSession:
    session = web_auth.resolve_session(db, request.cookies.get(COOKIE))
    if session is None:
        raise HTTPException(status_code=401, detail="وارد نشده‌ای")
    return session


def require_admin(
    session: WebSession = Depends(current_session), db: Session = Depends(get_db)
) -> WebSession:
    if not web_auth.is_admin(db, session.person_id, session.telegram_user_id):
        raise HTTPException(status_code=403, detail="دسترسی به این بخش مجاز نیست")
    return session


def current_person(
    session: WebSession = Depends(current_session), db: Session = Depends(get_db)
) -> Person:
    person = db.get(Person, session.person_id)
    if person is None:
        raise HTTPException(status_code=401, detail="وارد نشده‌ای")
    return person
