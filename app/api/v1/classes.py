"""Class type endpoints. Listing is open to any authenticated user;
mutations are admin only. Classes are deactivated, never deleted."""

from fastapi import APIRouter

from app.api.deps import AdminPerson, CurrentPerson, DbDep
from app.schemas.entities import ClassTypeCreateIn, ClassTypeOut, ClassTypeUpdateIn
from app.services import classes as classes_service

router = APIRouter(prefix="/class-types", tags=["class-types"])


@router.get("", response_model=list[ClassTypeOut])
def list_class_types(
    db: DbDep, _: CurrentPerson, only_active: bool = False
) -> list[ClassTypeOut]:
    return [
        ClassTypeOut.model_validate(c)
        for c in classes_service.list_class_types(db, only_active=only_active)
    ]


@router.post("", response_model=ClassTypeOut, status_code=201)
def create_class_type(
    body: ClassTypeCreateIn, db: DbDep, _: AdminPerson
) -> ClassTypeOut:
    class_type = classes_service.create(
        db, title=body.title, description=body.description, sort_order=body.sort_order
    )
    return ClassTypeOut.model_validate(class_type)


@router.patch("/{class_type_id}", response_model=ClassTypeOut)
def update_class_type(
    class_type_id: int, body: ClassTypeUpdateIn, db: DbDep, _: AdminPerson
) -> ClassTypeOut:
    class_type = classes_service.update(
        db,
        class_type_id,
        title=body.title,
        description=body.description,
        active=body.active,
        sort_order=body.sort_order,
    )
    return ClassTypeOut.model_validate(class_type)
