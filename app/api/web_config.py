"""The coach's configuration on the web: settings, contact links, and messages to students."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.web_deps import require_admin
from app.bots.common import keyboards
from app.copy import admin_texts as A
from app.core.exceptions import ValidationError
from app.db.session import get_db
from app.models import Person, Role, WebSession
from app.models.setting import (
    KEY_COURSE_END_MESSAGE,
    KEY_DEFAULT_ALLOWED_ABSENCE,
    KEY_LOW_SESSION_THRESHOLD,
    KEY_NOTIFY_ON_ATTENDANCE,
    KEY_SIGNUP_URL,
    KEY_WEB_REGISTRATION,
)
from app.notifications import service as notify_service
from app.services import contact_links as contact_links_service
from app.services import settings as settings_service

router = APIRouter(prefix="/api/admin", tags=["config"], dependencies=[Depends(require_admin)])

_TOGGLES = {KEY_NOTIFY_ON_ATTENDANCE, KEY_WEB_REGISTRATION}
_NUMBERS = {KEY_DEFAULT_ALLOWED_ABSENCE, KEY_LOW_SESSION_THRESHOLD}
_LINKS = {KEY_SIGNUP_URL}
# Messages the coach words himself: shown in a multi-line box.
_LONG = {
    "main_intro_message", "registration_contact_message", "plan_order_message",
    "contact_intro_message", KEY_COURSE_END_MESSAGE,
}


class Saved(BaseModel):
    ok: bool = True
    message: str


# --- settings ---


class SettingView(BaseModel):
    key: str
    label: str
    kind: str  # text | long | number | toggle | link
    value: str


class SettingIn(BaseModel):
    value: str = Field(max_length=4000)


def _kind(key: str) -> str:
    if key in _TOGGLES:
        return "toggle"
    if key in _NUMBERS:
        return "number"
    if key in _LINKS:
        return "link"
    return "long" if key in _LONG else "text"


@router.get("/settings", response_model=list[SettingView], operation_id="settings_list")
def list_settings(db: Session = Depends(get_db)) -> list[SettingView]:
    return [
        SettingView(
            key=key, label=label, kind=_kind(key), value=settings_service.get_value(db, key)
        )
        for key, label in A.SETTINGS_LABELS.items()
    ]


@router.put("/settings/{key}", response_model=Saved, operation_id="setting_save")
def save_setting(key: str, body: SettingIn, db: Session = Depends(get_db)) -> Saved:
    if key not in A.SETTINGS_LABELS:
        raise ValidationError("این تنظیم وجود ندارد")
    value = body.value.strip()
    kind = _kind(key)
    if kind == "toggle":
        value = "1" if value.lower() in {"1", "true", "on"} else "0"
    elif kind == "number":
        if not value.isdigit():
            raise ValidationError("این مقدار باید یک عدد باشد (مثلاً 2)")
    elif kind == "link":
        if not keyboards.is_button_url(value):
            raise ValidationError("این مقدار باید یک لینک کامل باشد که با https:// شروع شود")
    elif not value:
        raise ValidationError("مقدار نباید خالی باشد")
    settings_service.set_value(db, key, value)
    return Saved(message="تنظیمات ذخیره شد.")


# --- contact links ---


class LinkView(BaseModel):
    id: int
    label: str
    url: str
    icon: str | None
    active: bool


class LinkPatch(BaseModel):
    label: str | None = Field(default=None, max_length=120)
    url: str | None = Field(default=None, max_length=500)
    active: bool | None = None


class MoveIn(BaseModel):
    direction: int = Field(description="-1 up, +1 down")


def _link(link) -> LinkView:
    return LinkView(id=link.id, label=link.label, url=link.url, icon=link.icon, active=link.active)


@router.get("/contacts", response_model=list[LinkView], operation_id="contacts_list")
def list_contacts(db: Session = Depends(get_db)) -> list[LinkView]:
    return [_link(link) for link in contact_links_service.list_all(db)]


@router.patch("/contacts/{link_id}", response_model=LinkView, operation_id="contact_update")
def update_contact(link_id: int, body: LinkPatch, db: Session = Depends(get_db)) -> LinkView:
    link = contact_links_service.update(
        db, link_id, label=body.label, url=body.url, active=body.active
    )
    return _link(link)


@router.post("/contacts/{link_id}/move", response_model=Saved, operation_id="contact_move")
def move_contact(link_id: int, body: MoveIn, db: Session = Depends(get_db)) -> Saved:
    contact_links_service.move(db, link_id, -1 if body.direction < 0 else 1)
    return Saved(message="ترتیب عوض شد.")


# --- messages to students ---


class Audience(BaseModel):
    count: int


class BroadcastIn(BaseModel):
    text: str = Field(min_length=1, max_length=3500)


class Queued(BaseModel):
    count: int
    message: str


@router.get("/notify/audience", response_model=Audience, operation_id="notify_audience")
def audience(db: Session = Depends(get_db)) -> Audience:
    """Active students the bot can reach — what a broadcast would go to."""
    clients = db.scalars(
        select(Person).where(Person.role == Role.CLIENT, Person.is_active.is_(True))
    ).all()
    return Audience(count=sum(1 for c in clients if c.identities))


@router.post("/notify/broadcast", response_model=Queued, operation_id="notify_broadcast")
def broadcast(
    body: BroadcastIn, session: WebSession = Depends(require_admin), db: Session = Depends(get_db)
) -> Queued:
    count = notify_service.broadcast(
        db, body.text.strip(), created_by=str(session.telegram_user_id or session.person_id)
    )
    notify_service.dispatch_due(db)
    return Queued(count=count, message=f"پیام برای {count} شاگرد ارسال شد.")


@router.post("/notify/low-sessions", response_model=Queued, operation_id="notify_low_sessions")
def low_sessions(db: Session = Depends(get_db)) -> Queued:
    count = notify_service.generate_reminders(db)
    notify_service.dispatch_due(db)
    return Queued(count=count, message=f"یادآوری برای {count} شاگرد ارسال شد.")
