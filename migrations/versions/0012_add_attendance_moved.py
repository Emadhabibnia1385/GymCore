"""add the MOVED attendance status and attendance_events.moved_to

A session the coach reschedules by arrangement is recorded as MOVED on its
original date, carrying the new date in ``moved_to``; the derived grid then
shows the new date in its place.

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-10 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0012'
down_revision: str | None = '0011'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_VALUES = ('PRESENT', 'ABSENT_ALLOWED', 'ABSENT_UNAUTHORIZED', 'COACH_CANCELLED', 'HOLIDAY')
_NEW_VALUES = _OLD_VALUES + ('MOVED',)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        # Native enum: extend the type in its own transaction.
        with op.get_context().autocommit_block():
            op.execute("ALTER TYPE attendancestatus ADD VALUE IF NOT EXISTS 'MOVED'")
    else:
        # SQLite stores the enum as VARCHAR + CHECK, so the table is rebuilt.
        with op.batch_alter_table('attendance_events', schema=None) as batch_op:
            batch_op.alter_column(
                'status',
                existing_type=sa.Enum(*_OLD_VALUES, name='attendancestatus'),
                type_=sa.Enum(*_NEW_VALUES, name='attendancestatus'),
                existing_nullable=False,
            )

    with op.batch_alter_table('attendance_events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('moved_to', sa.Date(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('attendance_events', schema=None) as batch_op:
        batch_op.drop_column('moved_to')
    # Drop any rows using the removed value, then narrow the type back.
    op.execute("DELETE FROM attendance_events WHERE status = 'MOVED'")
    if op.get_bind().dialect.name != 'postgresql':
        with op.batch_alter_table('attendance_events', schema=None) as batch_op:
            batch_op.alter_column(
                'status',
                existing_type=sa.Enum(*_NEW_VALUES, name='attendancestatus'),
                type_=sa.Enum(*_OLD_VALUES, name='attendancestatus'),
                existing_nullable=False,
            )
