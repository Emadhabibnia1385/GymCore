"""Settings seeding + catalogs (contact links, plan types, class types)."""

import pytest

from app.core.exceptions import ValidationError
from app.models import Platform
from app.models.setting import (
    KEY_LOW_SESSION_THRESHOLD,
    KEY_NOTIFY_ON_ATTENDANCE,
    KEY_REGISTER_CONTACT_TEXT,
)
from app.services import classes as classes_service
from app.services import contact_links as contact_links_service
from app.services import persons as persons_service
from app.services import plans as plans_service
from app.services import settings as settings_service


def test_settings_seed_and_override(db):
    assert settings_service.get_value(db, KEY_REGISTER_CONTACT_TEXT)  # seeded, non-empty
    assert settings_service.get_int(db, KEY_LOW_SESSION_THRESHOLD) == 2
    assert settings_service.get_bool(db, KEY_NOTIFY_ON_ATTENDANCE) is True
    settings_service.set_value(db, KEY_REGISTER_CONTACT_TEXT, "متن تازه")
    assert settings_service.get_value(db, KEY_REGISTER_CONTACT_TEXT) == "متن تازه"


def test_contact_links_seed_and_platform_feature(db):
    active = contact_links_service.list_active(db)
    assert len(active) == 7
    featured = contact_links_service.list_active(db, Platform.TELEGRAM)
    assert featured[0].key == "telegram"


def test_contact_links_crud_and_reorder(db):
    link = contact_links_service.create(db, key="eitaa", label="ایتا", url="https://eitaa.com/x")
    assert link.sort_order == 8
    contact_links_service.set_active(db, link.id, False)
    assert len(contact_links_service.list_active(db)) == 7
    with pytest.raises(ValidationError):
        contact_links_service.create(db, key="x", label="", url="")


def test_plan_types_seeded_and_assignment(db):
    keys = {t.key for t in plans_service.list_types(db)}
    assert {"nutrition", "training", "specialized"} <= keys
    client = persons_service.create(db, name="کاربر")
    training = plans_service.get_type_by_key(db, "training")
    plans_service.create_assignment(
        db, person_id=client.id, plan_type_id=training.id, title="برنامه من", notify=False
    )
    assert len(plans_service.list_assignments(db, person_id=client.id)) == 1


def test_plan_attachment_validation(db):
    with pytest.raises(ValidationError):
        plans_service.save_attachment("malware.exe", b"x")


def test_class_types_seeded_and_create(db):
    assert len(classes_service.list_class_types(db, only_active=True)) == 3
    yoga = classes_service.create(db, title="یوگا")
    assert yoga.key  # auto-generated
    classes_service.set_active(db, yoga.id, False)
    assert len(classes_service.list_class_types(db, only_active=True)) == 3
