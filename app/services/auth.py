"""Admin authorization.

Root of trust is the numeric owner-ID whitelist (env). A person may ALSO be an
admin via a COACH/ADMIN database role, but that role is itself only ever granted
to a configured owner (see `sync_owner_role`). Usernames are never trusted.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.admin_auth import is_owner
from app.core.exceptions import AuthError
from app.models import Person, Platform, Role
from app.services import identities as identities_service


def is_admin(db: Session, platform: Platform, user_id: object) -> bool:
    if is_owner(platform, user_id):
        return True
    person = identities_service.find_person(db, platform, str(user_id))
    return person is not None and person.role in (Role.COACH, Role.ADMIN)


def ensure_admin(db: Session, platform: Platform, user_id: object) -> None:
    if not is_admin(db, platform, user_id):
        raise AuthError("دسترسی به این بخش مجاز نیست")


def sync_owner_role(db: Session, platform: Platform, user_id: object, person: Person) -> None:
    """Promote a configured owner's Person to COACH so the DB reflects reality."""
    if is_owner(platform, user_id) and person.role == Role.CLIENT:
        person.role = Role.COACH
        db.commit()
