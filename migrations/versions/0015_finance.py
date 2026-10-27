"""add expenses — the gym's costs, for the in-bot monthly finance report

The coach can now record what the gym spends (rent, equipment, salaries, ads,
bills) next to the payments he already records, and see each Jalali month's
income, expenses and net profit in the bot. Like payments, expenses are
append-only: a wrong entry is corrected by a negative one, never edited.

`category` is VARCHAR rather than a native enum, so a later category needs no
Postgres ALTER TYPE. A new, empty table — nothing existing is touched, so the
downgrade only has to drop it.

Revision ID: 0015
Revises: 0014
Create Date: 2026-10-27 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0015'
down_revision: str | None = '0014'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'expenses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.BigInteger(), nullable=False),
        sa.Column('category', sa.String(length=20), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('spent_at', sa.Date(), nullable=False),
        sa.Column('created_by', sa.String(length=64), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('expenses', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_expenses_spent_at'), ['spent_at'], unique=False)


def downgrade() -> None:
    # Drops the coach's recorded expenses with the table: back up first
    # (deploy/backup.sh runs before every install and update).
    with op.batch_alter_table('expenses', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_expenses_spent_at'))
    op.drop_table('expenses')
