"""Authentication for the web dashboard and REST API."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AuthError
from app.core.phone import normalize_phone
from app.core.security import create_access_token, decode_access_token, verify_password
from app.models import Person, Role
from app.services import persons as persons_service

logger = logging.getLogger(__name__)


def authenticate(db: Session, phone: str, password: str) -> Person:
    person = persons_service.get_by_phone(db, phone)
    if (
        person is None
        or not person.is_active
        or not person.password_hash
        or not verify_password(password, person.password_hash)
    ):
        raise AuthError("شماره موبایل یا رمز عبور اشتباه است")
    return person


def login(db: Session, phone: str, password: str) -> tuple[Person, str]:
    person = authenticate(db, phone, password)
    token = create_access_token(person.id, person.role.value)
    return person, token


def resolve_token(db: Session, token: str) -> Person | None:
    """Return the active person for a token, or None."""
    payload = decode_access_token(token)
    if payload is None:
        return None
    person = db.get(Person, int(payload["sub"]))
    if person is None or not person.is_active:
        return None
    return person


def bootstrap_admin(db: Session) -> None:
    """Create the initial admin from .env on first startup."""
    settings = get_settings()
    if not settings.admin_phone or not settings.admin_password:
        logger.warning("ADMIN_PHONE/ADMIN_PASSWORD not set — skipping admin bootstrap")
        return
    phone = normalize_phone(settings.admin_phone)
    existing = db.scalar(select(Person).where(Person.phone == phone))
    if existing is not None:
        return
    admin = persons_service.create(
        db, name=settings.admin_name, phone=phone, role=Role.ADMIN
    )
    persons_service.set_web_password(db, admin.id, settings.admin_password)
    logger.info("Bootstrap admin created: %s", phone)
