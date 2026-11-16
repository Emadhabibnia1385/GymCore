"""add web_login_requests — «log in with the bot» for the web panel

Revision ID: 0020
Revises: 0019
Create Date: 2026-11-16 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0020'
down_revision: str | None = '0019'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'web_login_requests',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('secret_hash', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=12), nullable=False),
        sa.Column('person_id', sa.Integer(), sa.ForeignKey('persons.id'), nullable=True),
        sa.Column('telegram_user_id', sa.String(length=32), nullable=True),
        sa.Column('user_agent', sa.String(length=200), nullable=True),
        sa.Column('client_ip', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_web_login_requests_token_hash', 'web_login_requests', ['token_hash'], unique=True)
    op.create_index('ix_web_login_requests_secret_hash', 'web_login_requests', ['secret_hash'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_web_login_requests_secret_hash', table_name='web_login_requests')
    op.drop_index('ix_web_login_requests_token_hash', table_name='web_login_requests')
    op.drop_table('web_login_requests')
