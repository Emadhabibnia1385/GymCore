"""Gym expenses — APPEND-ONLY, like payments.

The coach's own spending (rent, equipment, salaries, ads, bills) lives here so
the monthly report can show what is left once costs are paid. Rows are never
updated or deleted: a wrong entry is corrected by recording a NEGATIVE expense
in the same category, so every report can be re-derived from the history and
nothing silently disappears.
"""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExpenseCategory(str, enum.Enum):
    RENT = "RENT"
    EQUIPMENT = "EQUIPMENT"
    SALARY = "SALARY"
    ADS = "ADS"
    BILLS = "BILLS"
    OTHER = "OTHER"


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Toman, integer, never zero. A negative amount corrects an earlier entry.
    amount: Mapped[int] = mapped_column(BigInteger)
    # Plain VARCHAR rather than a native enum, so a later category needs no
    # Postgres ALTER TYPE.
    category: Mapped[ExpenseCategory] = mapped_column(
        Enum(ExpenseCategory, native_enum=False, length=20)
    )
    note: Mapped[str | None] = mapped_column(Text)
    # The day the money went out — what the monthly report groups by.
    spent_at: Mapped[date] = mapped_column(Date, index=True)
    # Audit: numeric platform user ID of the admin who recorded the expense.
    created_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Expense {self.id} {self.category.value} {self.amount}>"
