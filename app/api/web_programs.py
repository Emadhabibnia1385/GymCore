"""Programs and packages on the web: send a program to a student (with a file from the
computer), manage program types, and build packages for many students.

A package's *files and videos* are Telegram file_ids, which only a bot upload can
make, so the web adds and orders text items and says so; a file item is added in the bot.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.web_deps import require_admin
from app.core.exceptions import NotFoundError, ValidationError
from app.db.session import get_db
from app.models import Person, Role, WebSession
from app.services import packages as packages_service
from app.services import persons as persons_service
from app.services import plans as plans_service

router = APIRouter(prefix="/api/admin", tags=["programs"], dependencies=[Depends(require_admin)])


class Saved(BaseModel):
    ok: bool = True
    message: str


class Created(BaseModel):
    id: int
    message: str


def _by(session: WebSession) -> str:
    return str(session.telegram_user_id or f"web:{session.person_id}")


# --- program types ---


class TypeView(BaseModel):
    id: int
    title: str
    active: bool


class TypeIn(BaseModel):
    title: str = Field(min_length=1, max_length=150)


class TypePatch(BaseModel):
    title: str | None = Field(default=None, max_length=150)
    active: bool | None = None


@router.get("/program-types", response_model=list[TypeView], operation_id="program_types")
def program_types(db: Session = Depends(get_db)) -> list[TypeView]:
    return [TypeView(id=t.id, title=t.title, active=t.active) for t in plans_service.list_types(db)]


@router.post("/program-types", response_model=Created, operation_id="program_type_create")
def create_type(body: TypeIn, db: Session = Depends(get_db)) -> Created:
    made = plans_service.create_type(db, title=body.title)
    return Created(id=made.id, message="نوع برنامه ساخته شد.")


@router.patch("/program-types/{type_id}", response_model=Saved, operation_id="program_type_update")
def update_type(type_id: int, body: TypePatch, db: Session = Depends(get_db)) -> Saved:
    plans_service.update_type(db, type_id, title=body.title, active=body.active)
    return Saved(message="ذخیره شد.")


@router.delete("/program-types/{type_id}", response_model=Saved, operation_id="program_type_delete")
def delete_type(type_id: int, db: Session = Depends(get_db)) -> Saved:
    plans_service.delete_type(db, type_id)  # refuses a type that was used
    return Saved(message="نوع برنامه حذف شد.")


# --- sending a program to a student ---


@router.post("/programs", response_model=Created, operation_id="program_send")
async def send_program(
    person_id: int = Form(),
    plan_type_id: int = Form(),
    note: str = Form(default="", max_length=3500),
    file: UploadFile | None = File(default=None),
    session: WebSession = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Created:
    """A program for one student: a note, a file, or both — never neither."""
    persons_service.get(db, person_id)
    stored = original = None
    if file is not None and file.filename:
        original = file.filename[:200]
        stored = plans_service.save_attachment(original, await file.read())
    if stored is None and not note.strip():
        raise ValidationError("برنامه باید فایل یا متن داشته باشد")
    assignment = plans_service.create_assignment(
        db, person_id=person_id, plan_type_id=plan_type_id, coach_note=note.strip() or None,
        file_path=stored, original_filename=original, created_by=_by(session), notify=True,
    )
    return Created(id=assignment.id, message="برنامه برای شاگرد ثبت شد؛ از «برنامه‌های من» می‌بیند.")


# --- packages ---


class ItemView(BaseModel):
    id: int
    title: str | None
    kind: str
    text: str | None
    on_telegram: bool
    on_bale: bool


class PackageRow(BaseModel):
    id: int
    title: str
    active: bool
    items: int
    recipients: int


class RecipientView(BaseModel):
    assignment_id: int
    person_id: int
    name: str


class PackageDetail(PackageRow):
    description: str | None
    item_list: list[ItemView]
    recipient_list: list[RecipientView]
    ever_assigned: bool


class PackageIn(BaseModel):
    title: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=1500)


class PackagePatch(BaseModel):
    title: str | None = Field(default=None, max_length=150)
    description: str | None = Field(default=None, max_length=1500)
    active: bool | None = None


class TextItemIn(BaseModel):
    title: str | None = Field(default=None, max_length=150)
    text: str = Field(min_length=1, max_length=3500)


class ItemPatch(BaseModel):
    title: str | None = Field(default=None, max_length=150)
    text: str | None = Field(default=None, max_length=3500)


class MoveIn(BaseModel):
    direction: int


class AssignIn(BaseModel):
    person_ids: list[int] = Field(min_length=1, max_length=500)


class Assigned(BaseModel):
    count: int
    message: str


@router.get("/packages", response_model=list[PackageRow], operation_id="packages_list")
def list_packages(db: Session = Depends(get_db)) -> list[PackageRow]:
    packages = packages_service.list_packages(db)
    ids = [p.id for p in packages]
    items = packages_service.item_counts(db, ids)
    people = packages_service.recipient_counts(db, ids)
    return [
        PackageRow(
            id=p.id, title=p.title, active=p.active, items=items.get(p.id, 0),
            recipients=people.get(p.id, 0),
        )
        for p in packages
    ]


def _detail(db: Session, package_id: int) -> PackageDetail:
    package = packages_service.get(db, package_id)
    items = packages_service.items(db, package.id)
    people = packages_service.recipients(db, package.id)
    return PackageDetail(
        id=package.id, title=package.title, active=package.active, items=len(items),
        recipients=len(people), description=package.description,
        item_list=[
            ItemView(
                id=i.id, title=i.title, kind=i.kind, text=i.text,
                on_telegram=bool(i.telegram_file_id), on_bale=bool(i.bale_file_id),
            )
            for i in items
        ],
        recipient_list=[
            RecipientView(assignment_id=a.id, person_id=a.person_id, name=a.person.name)
            for a in people
        ],
        ever_assigned=packages_service.ever_assigned(db, package.id),
    )


@router.post("/packages", response_model=Created, operation_id="package_create")
def create_package(
    body: PackageIn, session: WebSession = Depends(require_admin), db: Session = Depends(get_db)
) -> Created:
    package = packages_service.create(
        db, body.title, description=body.description, created_by=_by(session)
    )
    return Created(id=package.id, message="پکیج ساخته شد.")


@router.get("/packages/{package_id}", response_model=PackageDetail, operation_id="package_get")
def get_package(package_id: int, db: Session = Depends(get_db)) -> PackageDetail:
    return _detail(db, package_id)


@router.patch("/packages/{package_id}", response_model=PackageDetail, operation_id="package_update")
def update_package(
    package_id: int, body: PackagePatch, db: Session = Depends(get_db)
) -> PackageDetail:
    if body.title is not None or body.description is not None:
        packages_service.update(db, package_id, title=body.title, description=body.description)
    if body.active is not None:
        packages_service.set_active(db, package_id, body.active)
    return _detail(db, package_id)


@router.delete("/packages/{package_id}", response_model=Saved, operation_id="package_delete")
def delete_package(package_id: int, db: Session = Depends(get_db)) -> Saved:
    packages_service.delete(db, package_id)  # refuses a package that was ever sent
    return Saved(message="پکیج حذف شد.")


@router.post(
    "/packages/{package_id}/items", response_model=PackageDetail, operation_id="package_item_add",
)
def add_item(package_id: int, body: TextItemIn, db: Session = Depends(get_db)) -> PackageDetail:
    packages_service.add_item(db, package_id, kind="text", text=body.text, title=body.title)
    return _detail(db, package_id)


def _item_package(db: Session, item_id: int) -> int:
    item = packages_service.find_item(db, item_id)
    if item is None:
        raise NotFoundError("مورد پیدا نشد")
    return item.package_id


@router.patch(
    "/package-items/{item_id}", response_model=PackageDetail, operation_id="package_item_update",
)
def update_item(item_id: int, body: ItemPatch, db: Session = Depends(get_db)) -> PackageDetail:
    package_id = _item_package(db, item_id)
    packages_service.update_item(db, item_id, text=body.text, title=body.title)
    return _detail(db, package_id)


@router.post(
    "/package-items/{item_id}/move", response_model=PackageDetail, operation_id="package_item_move",
)
def move_item(item_id: int, body: MoveIn, db: Session = Depends(get_db)) -> PackageDetail:
    package_id = _item_package(db, item_id)
    packages_service.move_item(db, item_id, -1 if body.direction < 0 else 1)
    return _detail(db, package_id)


@router.delete(
    "/package-items/{item_id}", response_model=PackageDetail, operation_id="package_item_delete",
)
def delete_item(item_id: int, db: Session = Depends(get_db)) -> PackageDetail:
    package_id = _item_package(db, item_id)
    packages_service.delete_item(db, item_id)
    return _detail(db, package_id)


@router.post(
    "/packages/{package_id}/assign", response_model=Assigned, operation_id="package_assign",
)
def assign_package(
    package_id: int, body: AssignIn, session: WebSession = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Assigned:
    for person_id in body.person_ids:
        person = db.get(Person, person_id)
        if person is None or person.role != Role.CLIENT:
            raise NotFoundError("شاگرد پیدا نشد")
    newly = packages_service.assign(db, package_id, body.person_ids, created_by=_by(session))
    return Assigned(count=len(newly), message=f"پکیج برای {len(newly)} شاگرد فعال شد.")


@router.post(
    "/package-assignments/{assignment_id}/revoke",
    response_model=Saved,
    operation_id="package_revoke",
)
def revoke(assignment_id: int, db: Session = Depends(get_db)) -> Saved:
    packages_service.unassign(db, assignment_id)
    return Saved(message="دسترسی شاگرد به این پکیج برداشته شد.")
