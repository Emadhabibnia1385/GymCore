"""Class types the coach offers (e.g. بدنسازی، کراس‌فیت، TRX)."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ClassType(Base):
    __tablename__ = "class_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(default=True, index=True)
    # Display order in menus/lists ("order" is an SQL keyword, hence sort_order).
    sort_order: Mapped[int] = mapped_column(default=0)
