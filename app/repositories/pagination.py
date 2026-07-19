"""Tiny pagination helper for admin lists (keeps buttons per message bounded)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session


@dataclass
class Page:
    items: list[Any]
    total: int
    page: int
    per_page: int

    @property
    def pages(self) -> int:
        return max((self.total + self.per_page - 1) // self.per_page, 1)

    @property
    def has_prev(self) -> bool:
        return self.page > 1

    @property
    def has_next(self) -> bool:
        return self.page < self.pages


def paginate(db: Session, stmt: Select, page: int = 1, per_page: int = 8) -> Page:
    """Run `stmt` for one page and return items + navigation metadata."""
    page = max(int(page or 1), 1)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    items = list(db.scalars(stmt.limit(per_page).offset((page - 1) * per_page)))
    return Page(items=items, total=total, page=page, per_page=per_page)
