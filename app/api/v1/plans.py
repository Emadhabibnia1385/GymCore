"""Plan endpoints, including secure attachment download.

Attachments are never served as public static files — the download route
checks that the requester is an admin or the plan's owner.
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import AdminPerson, CurrentPerson, DbDep
from app.models import Plan, PlanType, Role
from app.schemas.entities import PlanOut
from app.services import plans as plans_service

router = APIRouter(prefix="/plans", tags=["plans"])


def _to_out(plan: Plan) -> PlanOut:
    out = PlanOut.model_validate(plan)
    out.has_file = bool(plan.file_path)
    return out


@router.get("", response_model=list[PlanOut])
def list_plans(
    db: DbDep,
    person: CurrentPerson,
    person_id: int | None = None,
    only_active: bool = False,
) -> list[PlanOut]:
    if person.role != Role.ADMIN:
        person_id = person.id
    return [
        _to_out(p)
        for p in plans_service.list_plans(db, person_id=person_id, only_active=only_active)
    ]


@router.post("", response_model=PlanOut, status_code=201)
async def create_plan(
    db: DbDep,
    _: AdminPerson,
    person_id: int = Form(...),
    plan_type: PlanType = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    file: UploadFile | None = File(None),
) -> PlanOut:
    stored_name = None
    original_filename = None
    if file is not None and file.filename:
        content = await file.read()
        stored_name = plans_service.save_attachment(file.filename, content)
        original_filename = file.filename
    plan = plans_service.create(
        db,
        person_id=person_id,
        plan_type=plan_type,
        title=title,
        description=description or None,
        file_path=stored_name,
        original_filename=original_filename,
    )
    return _to_out(plan)


@router.patch("/{plan_id}/active", response_model=PlanOut)
def set_plan_active(
    plan_id: int, active: bool, db: DbDep, _: AdminPerson
) -> PlanOut:
    return _to_out(plans_service.set_active(db, plan_id, active))


@router.get("/{plan_id}/file")
def download_plan_file(plan_id: int, db: DbDep, person: CurrentPerson) -> FileResponse:
    plan = plans_service.get(db, plan_id)
    if person.role != Role.ADMIN and plan.person_id != person.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    path = plans_service.attachment_path(plan)
    if path is None:
        raise HTTPException(status_code=404, detail="No file attached")
    return FileResponse(
        path, filename=plan.original_filename or path.name
    )
