"""Profile photos: one small square image per person.

A photo is never kept as sent: it is opened as an image (PNG, JPEG or WebP, size-limited,
fully decoded), cropped to a centred square, shrunk and re-encoded as PNG under
`<upload_dir>/avatars/<person id>.png`. `Person.avatar_version` rises with every change and
rides in the URL, so browsers refetch.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageOps
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Person
from app.services import branding
from app.services import persons as persons_service

SIDE = 256


def _dir() -> Path:
    path = get_settings().upload_dir / "avatars"
    path.mkdir(parents=True, exist_ok=True)
    return path


def path_of(person_id: int) -> Path:
    return _dir() / f"{int(person_id)}.png"


def save(db: Session, person_id: int, content: bytes) -> Person:
    person = persons_service.get(db, person_id)
    image = ImageOps.fit(branding._open(content), (SIDE, SIDE), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, "PNG", optimize=True)
    path_of(person.id).write_bytes(buffer.getvalue())
    person.avatar_version = (person.avatar_version or 0) + 1
    db.commit()
    return person


def remove(db: Session, person_id: int) -> Person:
    person = persons_service.get(db, person_id)
    path_of(person.id).unlink(missing_ok=True)
    person.avatar_version = 0
    db.commit()
    return person
