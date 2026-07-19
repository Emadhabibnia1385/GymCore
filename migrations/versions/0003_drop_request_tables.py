"""drop class registration + plan request tables

The in-bot request flows were replaced: «سفارش برنامه» now opens a signup
Mini App and «ثبت‌نام کلاس» shows the contact methods, so these two tables
(and the now-unused ``requeststatus`` enum) are removed.

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-19 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('plan_requests', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_plan_requests_status'))
        batch_op.drop_index(batch_op.f('ix_plan_requests_person_id'))
    op.drop_table('plan_requests')

    with op.batch_alter_table('class_registration_requests', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_class_registration_requests_status'))
        batch_op.drop_index(batch_op.f('ix_class_registration_requests_person_id'))
    op.drop_table('class_registration_requests')

    # `requeststatus` is no longer referenced by any table. On PostgreSQL the
    # enum type lingers after the tables are dropped, so remove it explicitly.
    # (SQLite has no separate enum type — nothing to do there.)
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        sa.Enum(name='requeststatus').drop(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    # `plantype` still exists (used by `plans`); `requeststatus` was dropped in
    # upgrade, so recreate only that one before the columns reference it.
    requeststatus = sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='requeststatus')
    if bind.dialect.name == 'postgresql':
        requeststatus.create(bind, checkfirst=True)

    op.create_table(
        'class_registration_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=False),
        sa.Column('class_type_id', sa.Integer(), nullable=False),
        sa.Column('note', sa.String(length=500), nullable=True),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='requeststatus', create_type=False),
            nullable=False,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['class_type_id'], ['class_types.id']),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('class_registration_requests', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_class_registration_requests_person_id'), ['person_id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_class_registration_requests_status'), ['status'], unique=False
        )

    op.create_table(
        'plan_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=False),
        sa.Column(
            'plan_type',
            sa.Enum('TRAINING', 'NUTRITION', 'CUSTOM', name='plantype', create_type=False),
            nullable=False,
        ),
        sa.Column('note', sa.String(length=500), nullable=True),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'APPROVED', 'REJECTED', name='requeststatus', create_type=False),
            nullable=False,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('plan_requests', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_plan_requests_person_id'), ['person_id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_plan_requests_status'), ['status'], unique=False
        )
