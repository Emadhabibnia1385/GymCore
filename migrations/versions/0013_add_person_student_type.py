"""add persons.student_type (حضوری / غیرحضوری)

Splits the coach's student list into in-person and online students. Stored as
VARCHAR rather than a native enum, so a later type needs no ALTER TYPE.

Existing clients are backfilled from what they already have, so the split is
useful from the first deploy: a client with programs but no course trains
online; everyone else (courses, both, or neither) stays in person. The coach
can move anyone from the student's edit menu.

Revision ID: 0013
Revises: 0012
Create Date: 2026-09-14 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0013'
down_revision: str | None = '0012'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('persons', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                'student_type',
                sa.String(length=20),
                nullable=False,
                server_default='IN_PERSON',
            )
        )
        batch_op.create_index('ix_persons_student_type', ['student_type'], unique=False)

    op.execute(
        "UPDATE persons SET student_type = 'ONLINE' "
        "WHERE role = 'CLIENT' "
        "AND id IN (SELECT person_id FROM plan_assignments) "
        "AND id NOT IN (SELECT client_id FROM courses)"
    )


def downgrade() -> None:
    with op.batch_alter_table('persons', schema=None) as batch_op:
        batch_op.drop_index('ix_persons_student_type')
        batch_op.drop_column('student_type')
