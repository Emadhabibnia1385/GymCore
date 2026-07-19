"""Plan catalog — the kinds of programs the coach delivers.

Defaults (seeded): برنامه تغذیه اصولی، برنامه تمرینی اصولی، برنامه تمرینی تخصصی.
Rows referenced by historical assignments are deactivated, never deleted.
"""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlanType(Base):
    __tablename__ = "plan_types"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(150))
    active: Mapped[bool] = mapped_column(default=True, index=True)
    sort_order: Mapped[int] = mapped_column(default=0)
