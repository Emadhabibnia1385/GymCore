"""Coach contact links shown by «راه‌های ارتباطی ما» — admin-managed.

The runtime list is NEVER hardcoded in handlers; it is read from this table so
the coach can create/edit/activate/reorder links from the in-bot admin panel.
An optional `platform` hint lets a link be featured on one platform (e.g. the
Bale contact on Bale) while all links remain available everywhere.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import Platform


class ContactLink(Base):
    __tablename__ = "contact_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(500))
    icon: Mapped[str | None] = mapped_column(String(16))  # emoji, e.g. "✈️"
    active: Mapped[bool] = mapped_column(default=True, index=True)
    sort_order: Mapped[int] = mapped_column(default=0)
    # Optional prominence hint: feature this link on the given platform.
    platform: Mapped[Platform | None] = mapped_column(Enum(Platform))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
