"""Person management endpoints (admin only).

Persons are never hard-deleted — deactivate via PATCH is_active=false.
"""

from fastapi import APIRouter

from app.api.deps import AdminPerson, DbDep
from app.models import Role
from app.schemas.entities import (
    PersonCreateIn,
    PersonDetailOut,
    PersonOut,
    PersonUpdateIn,
    SetPasswordIn,
)
from app.services import persons as persons_service

router = APIRouter(prefix="/persons", tags=["persons"])


@router.get("", response_model=list[PersonOut])
def list_persons(
    db: DbDep, _: AdminPerson, role: Role | None = None, search: str | None = None
) -> list[PersonOut]:
    return [
        PersonOut.model_validate(p)
        for p in persons_service.list_persons(db, role=role, search=search)
    ]


@router.post("", response_model=PersonOut, status_code=201)
def create_person(body: PersonCreateIn, db: DbDep, _: AdminPerson) -> PersonOut:
    person = persons_service.create(
        db, name=body.name, phone=body.phone, role=body.role, note=body.note
    )
    return PersonOut.model_validate(person)


@router.get("/{person_id}", response_model=PersonDetailOut)
def get_person(person_id: int, db: DbDep, _: AdminPerson) -> PersonDetailOut:
    return PersonDetailOut.model_validate(persons_service.get(db, person_id))


@router.patch("/{person_id}", response_model=PersonOut)
def update_person(
    person_id: int, body: PersonUpdateIn, db: DbDep, _: AdminPerson
) -> PersonOut:
    person = persons_service.update(
        db,
        person_id,
        name=body.name,
        phone=body.phone,
        role=body.role,
        note=body.note,
        is_active=body.is_active,
    )
    return PersonOut.model_validate(person)


@router.post("/{person_id}/password", response_model=PersonOut)
def set_password(
    person_id: int, body: SetPasswordIn, db: DbDep, _: AdminPerson
) -> PersonOut:
    person = persons_service.set_web_password(db, person_id, body.password)
    return PersonOut.model_validate(person)
