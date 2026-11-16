"""The web panel's identity: its name, its browser-tab title, and two logos.

- a wide logo (login page and the menu's header) and a square icon (browser tab, the icon
  installed on a phone);
- stored as processed PNGs under `<upload_dir>/brand/`. An upload is never kept as sent:
  it is opened as an image, size-limited, and re-encoded, so a file that merely claims to be
  an image (or hides a script in an SVG) can't reach a visitor;
- `brand_version` changes with every logo edit and rides in the logo URLs, so browsers refetch.

The name is the existing `gym_name` setting (default «GymCore»).
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.models.setting import KEY_BRAND_VERSION, KEY_GYM_NAME, KEY_SITE_TITLE
from app.services import settings as settings_service

KINDS = ("wide", "icon")
_ALLOWED = {"PNG", "JPEG", "WEBP"}
MAX_BYTES = 5 * 1024 * 1024
_MAX_SIDE = 4096
_WIDE_MAX = (800, 240)
_ICON_SIZES = {"512": 512, "192": 192, "180": 180}
_NAME_MAX = 60
_TITLE_MAX = 80
_BLACK = (0, 0, 0, 255)  # the splash colour a maskable icon sits on


@dataclass(frozen=True)
class Brand:
    name: str
    title: str
    wide: bool
    icon: bool
    version: int


def _dir() -> Path:
    path = get_settings().upload_dir / "brand"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _file(name: str) -> Path:
    return _dir() / name


def get(db: Session) -> Brand:
    name = settings_service.get_value(db, KEY_GYM_NAME).strip() or "GymCore"
    return Brand(
        name=name,
        title=settings_service.get_value(db, KEY_SITE_TITLE).strip() or name,
        wide=_file("wide.png").is_file(),
        icon=_file("icon-512.png").is_file(),
        version=settings_service.get_int(db, KEY_BRAND_VERSION, 0),
    )


def set_texts(db: Session, name: str, title: str) -> None:
    name, title = " ".join(name.split()), " ".join(title.split())
    if not name:
        raise ValidationError("نام سایت نباید خالی باشد")
    if len(name) > _NAME_MAX or len(title) > _TITLE_MAX:
        raise ValidationError(f"نام حداکثر {_NAME_MAX} و عنوان حداکثر {_TITLE_MAX} نویسه باشد")
    settings_service.set_value(db, KEY_GYM_NAME, name)
    settings_service.set_value(db, KEY_SITE_TITLE, title or name)


def _bump(db: Session) -> None:
    settings_service.set_value(
        db, KEY_BRAND_VERSION, str(settings_service.get_int(db, KEY_BRAND_VERSION, 0) + 1)
    )


def _open(content: bytes) -> Image.Image:
    if len(content) > MAX_BYTES:
        raise ValidationError("حجم تصویر بیش از ۵ مگابایت است")
    try:
        image = Image.open(io.BytesIO(content))
        if image.format not in _ALLOWED:
            raise ValidationError("فرمت تصویر باید PNG، JPEG یا WebP باشد")
        if max(image.size) > _MAX_SIDE:
            raise ValidationError("ابعاد تصویر بیش از حد بزرگ است")
        image.load()  # decodes fully: a truncated or hostile file fails here, not later
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValidationError("این فایل تصویر معتبری نیست") from None
    return ImageOps.exif_transpose(image).convert("RGBA")


def _save(image: Image.Image, name: str) -> None:
    buffer = io.BytesIO()
    image.save(buffer, "PNG", optimize=True)
    _file(name).write_bytes(buffer.getvalue())


def _square(image: Image.Image, side: int, padding: float = 0.0, background=None) -> Image.Image:
    """The image centred on a square canvas, never cropped; padding keeps it inside a mask."""
    inner = max(1, round(side * (1 - 2 * padding)))
    fitted = ImageOps.contain(image, (inner, inner), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (side, side), background or (0, 0, 0, 0))
    canvas.paste(fitted, ((side - fitted.width) // 2, (side - fitted.height) // 2), fitted)
    return canvas


def save_logo(db: Session, kind: str, content: bytes) -> None:
    if kind not in KINDS:
        raise ValidationError("نوع لوگو نامعتبر است")
    image = _open(content)
    if kind == "wide":
        _save(ImageOps.contain(image, _WIDE_MAX, Image.Resampling.LANCZOS), "wide.png")
    else:
        for label, side in _ICON_SIZES.items():
            _save(_square(image, side), f"icon-{label}.png")
        _save(_square(image, 512, padding=0.12, background=_BLACK), "icon-maskable-512.png")
    _bump(db)


def remove_logo(db: Session, kind: str) -> None:
    if kind not in KINDS:
        raise ValidationError("نوع لوگو نامعتبر است")
    names = ["wide.png"] if kind == "wide" else [
        *(f"icon-{label}.png" for label in _ICON_SIZES), "icon-maskable-512.png",
    ]
    for name in names:
        _file(name).unlink(missing_ok=True)
    _bump(db)


def logo_path(kind: str, size: str | None = None) -> Path | None:
    """The stored PNG for a public URL, or None when none is set."""
    if kind == "wide":
        name = "wide.png"
    elif kind == "icon" and size in (*_ICON_SIZES, "maskable"):
        name = "icon-maskable-512.png" if size == "maskable" else f"icon-{size}.png"
    else:
        return None
    path = _file(name)
    return path if path.is_file() else None


def manifest(db: Session) -> dict:
    """The installable app's manifest, with the brand's name and icons."""
    brand = get(db)
    suffix = f"?v={brand.version}"
    icons = (
        [
            {"src": f"/api/brand/icon/192{suffix}", "sizes": "192x192", "type": "image/png"},
            {"src": f"/api/brand/icon/512{suffix}", "sizes": "512x512", "type": "image/png"},
            {"src": f"/api/brand/icon/maskable{suffix}", "sizes": "512x512",
             "type": "image/png", "purpose": "maskable"},
        ]
        if brand.icon
        else [
            {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/icons/icon-maskable-512.png", "sizes": "512x512",
             "type": "image/png", "purpose": "maskable"},
        ]
    )
    return {
        "name": brand.title, "short_name": brand.name[:12], "lang": "fa", "dir": "rtl",
        "start_url": "/", "scope": "/", "display": "standalone",
        "background_color": "#000000", "theme_color": "#000000", "icons": icons,
    }
