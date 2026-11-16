"""Profile photos on the web: a person changes their own; the coach sets any student's.

A photo is private to its owner and the coach: it is served only to them, never from a
public URL.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.web_deps import current_session, require_admin
from app.db.session import get_db
from app.models import Person, Role, WebSession
from app.services import avatars as avatars_service
from app.services import branding

router = APIRouter(prefix="/api", tags=["avatar"])


class Avatar(BaseModel):
    version: int  # 0: none


def _picture(person: Person) -> FileResponse:
    path = avatars_service.path_of(person.id)
    if not person.avatar_version or not path.is_file():
        raise HTTPException(status_code=404, detail="عکسی نیست")
    return FileResponse(
        path, media_type="image/png", headers={"Cache-Control": "private, max-age=86400"}
    )


async def _read(file: UploadFile) -> bytes:
    return await file.read(branding.MAX_BYTES + 1)


@router.get("/me/avatar", operation_id="my_avatar")
def my_avatar(
    session: WebSession = Depends(current_session), db: Session = Depends(get_db)
) -> FileResponse:
    return _picture(db.get(Person, session.person_id))


@router.post("/me/avatar", response_model=Avatar, operation_id="my_avatar_set")
async def set_my_avatar(
    file: UploadFile = File(),
    session: WebSession = Depends(current_session),
    db: Session = Depends(get_db),
) -> Avatar:
    person = avatars_service.save(db, session.person_id, await _read(file))
    return Avatar(version=person.avatar_version)


@router.delete("/me/avatar", response_model=Avatar, operation_id="my_avatar_remove")
def remove_my_avatar(
    session: WebSession = Depends(current_session), db: Session = Depends(get_db)
) -> Avatar:
    return Avatar(version=avatars_service.remove(db, session.person_id).avatar_version)


def _student(db: Session, person_id: int) -> Person:
    person = db.get(Person, person_id)
    if person is None or person.role != Role.CLIENT:
        raise HTTPException(status_code=404, detail="موردی پیدا نشد")
    return person


@router.get(
    "/admin/students/{person_id}/avatar", operation_id="student_avatar",
    dependencies=[Depends(require_admin)],
)
def student_avatar(person_id: int, db: Session = Depends(get_db)) -> FileResponse:
    return _picture(_student(db, person_id))


@router.post(
    "/admin/students/{person_id}/avatar", response_model=Avatar,
    operation_id="student_avatar_set", dependencies=[Depends(require_admin)],
)
async def set_student_avatar(
    person_id: int, file: UploadFile = File(), db: Session = Depends(get_db)
) -> Avatar:
    _student(db, person_id)
    person = avatars_service.save(db, person_id, await _read(file))
    return Avatar(version=person.avatar_version)


@router.delete(
    "/admin/students/{person_id}/avatar", response_model=Avatar,
    operation_id="student_avatar_remove", dependencies=[Depends(require_admin)],
)
def remove_student_avatar(person_id: int, db: Session = Depends(get_db)) -> Avatar:
    _student(db, person_id)
    return Avatar(version=avatars_service.remove(db, person_id).avatar_version)
