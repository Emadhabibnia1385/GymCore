"""web_login_requests.link_person_id — «connect Telegram» requests from a signed-in web account

Revision ID: 0021
Revises: 0020
Create Date: 2026-11-16 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0021'
down_revision: str | None = '0020'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('web_login_requests') as batch:
        batch.add_column(sa.Column('link_person_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('web_login_requests') as batch:
        batch.drop_column('link_person_id')
