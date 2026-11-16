"""persons.avatar_version — a profile photo (0 means none)

Revision ID: 0022
Revises: 0021
Create Date: 2026-11-16 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0022'
down_revision: str | None = '0021'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('persons') as batch:
        batch.add_column(sa.Column('avatar_version', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    with op.batch_alter_table('persons') as batch:
        batch.drop_column('avatar_version')
