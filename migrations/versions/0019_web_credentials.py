"""add web_credentials — username and password for the web panel

Also lets a web session have no Telegram id (a password session).

Revision ID: 0019
Revises: 0018
Create Date: 2026-11-16 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0019'
down_revision: str | None = '0018'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'web_credentials',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('person_id', sa.Integer(), sa.ForeignKey('persons.id'), nullable=False),
        sa.Column('username', sa.String(length=32), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('person_id', name='uq_web_credentials_person_id'),
    )
    op.create_index('ix_web_credentials_username', 'web_credentials', ['username'], unique=True)
    with op.batch_alter_table('web_sessions', schema=None) as batch_op:
        batch_op.alter_column('telegram_user_id', existing_type=sa.String(length=32), nullable=True)


def downgrade() -> None:
    # A password session has no Telegram id; it cannot exist in the older shape.
    op.execute("DELETE FROM web_sessions WHERE telegram_user_id IS NULL")
    with op.batch_alter_table('web_sessions', schema=None) as batch_op:
        batch_op.alter_column('telegram_user_id', existing_type=sa.String(length=32), nullable=False)
    op.drop_index('ix_web_credentials_username', table_name='web_credentials')
    op.drop_table('web_credentials')
