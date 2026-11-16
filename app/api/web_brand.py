"""The panel's identity over HTTP: a public read (the login page needs it before anyone is
signed in) and an admin write (the coach sets the name, the title and the logos)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.web_deps import require_admin
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.services import branding

public = APIRouter(prefix="/api/brand", tags=["brand"])
admin = APIRouter(
    prefix="/api/admin/brand", tags=["brand"], dependencies=[Depends(require_admin)]
)

# A logo URL carries the brand version, so a changed logo is a new URL; a day is plenty.
_CACHE = {"Cache-Control": "public, max-age=86400"}


class BrandView(BaseModel):
    name: str
    title: str
    wide: bool
    icon: bool
    version: int


class BrandTexts(BaseModel):
    name: str = Field(max_length=200)
    title: str = Field(default="", max_length=200)


def _view(db: Session) -> BrandView:
    b = branding.get(db)
    return BrandView(name=b.name, title=b.title, wide=b.wide, icon=b.icon, version=b.version)


@public.get("", response_model=BrandView, operation_id="brand_get")
def get_brand(db: Session = Depends(get_db)) -> BrandView:
    return _view(db)


@public.get("/manifest.webmanifest", include_in_schema=False)
def manifest(db: Session = Depends(get_db)) -> JSONResponse:
    return JSONResponse(
        branding.manifest(db), media_type="application/manifest+json",
        headers={"Cache-Control": "no-cache"},
    )


@public.get("/logo/{kind}", include_in_schema=False)
def logo(kind: str) -> FileResponse:
    path = branding.logo_path(kind)
    if path is None:
        raise NotFoundError("لوگو تنظیم نشده")
    return FileResponse(path, media_type="image/png", headers=_CACHE)


@public.get("/icon/{size}", include_in_schema=False)
def icon(size: str) -> FileResponse:
    path = branding.logo_path("icon", size)
    if path is None:
        raise NotFoundError("آیکن تنظیم نشده")
    return FileResponse(path, media_type="image/png", headers=_CACHE)


@admin.put("", response_model=BrandView, operation_id="brand_set_texts")
def set_texts(body: BrandTexts, db: Session = Depends(get_db)) -> BrandView:
    branding.set_texts(db, body.name, body.title)
    return _view(db)


@admin.post("/logo/{kind}", response_model=BrandView, operation_id="brand_upload_logo")
async def upload_logo(
    kind: str, file: UploadFile = File(), db: Session = Depends(get_db)
) -> BrandView:
    # Read one byte past the limit so an oversize file is refused without being held whole.
    content = await file.read(branding.MAX_BYTES + 1)
    branding.save_logo(db, kind, content)
    return _view(db)


@admin.delete("/logo/{kind}", response_model=BrandView, operation_id="brand_remove_logo")
def remove_logo(kind: str, db: Session = Depends(get_db)) -> BrandView:
    branding.remove_logo(db, kind)
    return _view(db)
