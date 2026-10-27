"""add plan_assignments.file_kind; add the «برنامه تمرینی» program type

A program file can now be a video as well as a document or a photo, and each
platform sends those with a different method (sendVideo / sendDocument /
sendPhoto). `file_kind` records which one the coach uploaded, so delivery makes
exactly one call. Rows from before stay NULL and keep the old document-then-
photo fallback.

The coach asked for training programs next to «تغذیه». The type is added here,
once, rather than seeded at startup: a seed would bring it back after the coach
renamed or deleted it.

Revision ID: 0014
Revises: 0013
Create Date: 2026-10-27 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0014'
down_revision: str | None = '0013'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('plan_assignments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('file_kind', sa.String(length=16), nullable=True))

    # A FROM-less SELECT so the WHERE can skip the insert entirely (an aggregate
    # over plan_types would always yield one row, and insert regardless).
    op.execute(
        "INSERT INTO plan_types (key, title, active, sort_order) "
        "SELECT 'training', 'برنامه تمرینی', TRUE, "
        "(SELECT COALESCE(MAX(sort_order), 0) + 1 FROM plan_types) "
        "WHERE NOT EXISTS ("
        "SELECT 1 FROM plan_types WHERE key = 'training' OR title = 'برنامه تمرینی')"
    )


def downgrade() -> None:
    # The program type stays: by now it may carry the coach's programs.
    with op.batch_alter_table('plan_assignments', schema=None) as batch_op:
        batch_op.drop_column('file_kind')
