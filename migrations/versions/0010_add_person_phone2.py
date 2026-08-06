"""add persons.phone2 (optional second contact number)

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-03 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0010'
down_revision: str | None = '0009'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('persons', schema=None) as batch_op:
        batch_op.add_column(sa.Column('phone2', sa.String(length=20), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('persons', schema=None) as batch_op:
        batch_op.drop_column('phone2')
