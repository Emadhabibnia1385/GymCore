"""add web_sessions — browser logins for the web panel

Revision ID: 0018
Revises: 0017
Create Date: 2026-11-16 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0018'
down_revision: str | None = '0017'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'web_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('person_id', sa.Integer(), sa.ForeignKey('persons.id'), nullable=False),
        sa.Column('telegram_user_id', sa.String(length=32), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('user_agent', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_web_sessions_person_id', 'web_sessions', ['person_id'])
    op.create_index('ix_web_sessions_token_hash', 'web_sessions', ['token_hash'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_web_sessions_token_hash', table_name='web_sessions')
    op.drop_index('ix_web_sessions_person_id', table_name='web_sessions')
    op.drop_table('web_sessions')
