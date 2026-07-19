"""Identity linking and admin authorization (numeric whitelist + DB role)."""

from app.models import Platform, Role
from app.services import auth
from app.services import identities as identities_service
from app.services import persons as persons_service


def test_auto_provision_and_cross_platform_link(db):
    person = identities_service.get_or_create_person(
        db, Platform.TELEGRAM, "1001", "علی رضایی", username="ali"
    )
    assert person.role == Role.CLIENT
    # Idempotent: same account returns the same person.
    again = identities_service.get_or_create_person(db, Platform.TELEGRAM, "1001", "x")
    assert again.id == person.id
    # Linking a Bale account to the same person unifies their data.
    identities_service.link_identity(db, person.id, Platform.BALE, "2002")
    assert identities_service.find_person(db, Platform.BALE, "2002").id == person.id
    assert identities_service.find_person(db, Platform.TELEGRAM, "9999") is None


def test_admin_numeric_whitelist(db):
    assert auth.is_admin(db, Platform.TELEGRAM, 111)
    assert auth.is_admin(db, Platform.TELEGRAM, "111")  # numeric string ok
    assert auth.is_admin(db, Platform.BALE, 333)
    # A non-owner is never admin, even trying another platform's owner id.
    assert not auth.is_admin(db, Platform.TELEGRAM, 999)
    assert not auth.is_admin(db, Platform.BALE, 111)


def test_admin_by_db_role(db):
    coach = persons_service.create(db, name="مربی", role=Role.COACH)
    identities_service.link_identity(db, coach.id, Platform.TELEGRAM, "5005")
    assert auth.is_admin(db, Platform.TELEGRAM, "5005")


def test_sync_owner_role_promotes(db):
    owner = identities_service.get_or_create_person(db, Platform.TELEGRAM, "111", "اونر")
    assert owner.role == Role.CLIENT
    auth.sync_owner_role(db, Platform.TELEGRAM, "111", owner)
    assert owner.role == Role.COACH
