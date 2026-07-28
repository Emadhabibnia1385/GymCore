"""course weekly training pattern (drives the derived session grid)

Adds `courses.weekdays` — Persian weekday indexes as a short CSV, e.g. "0,2,4"
for شنبه/دوشنبه/چهارشنبه.

Non-destructive: the column is nullable and existing rows stay NULL. Courses
without a pattern fall back to the start date's weekday
(services/schedule.py::course_weekdays), so old data keeps working.

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-28 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0007'
down_revision: str | None = '0006'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('courses', sa.Column('weekdays', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('courses', 'weekdays')
