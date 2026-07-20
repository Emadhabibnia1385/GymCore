"""drop default plan types if unused (coach creates their own)

Mirrors the class-type change: the seeded defaults (nutrition/training/
specialized) are removed unless an assignment references them.

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-20 01:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa  # noqa: F401


revision: str = '0006'
down_revision: str | None = '0005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "DELETE FROM plan_types "
        "WHERE key IN ('nutrition', 'training', 'specialized') "
        "AND id NOT IN (SELECT plan_type_id FROM plan_assignments)"
    )


def downgrade() -> None:
    pass
