"""add program packages — bundles built once and sent to many students

The coach asked to design courses that hold both a diet plan and training
videos. A package (program_packages) is that bundle; its items
(package_items) are files and text in order, and package_assignments records
which students have it. Students see the package's current items, so nothing
is copied per student.

A file item keeps one file_id per platform (telegram_file_id / bale_file_id):
a file_id only works on the platform that issued it.

One row per (package, student) — uq_package_person: revoking switches the row
off and sending again switches it back on. A student's rows go with the student
(ON DELETE CASCADE here; the ORM cascade covers SQLite, which enforces no
foreign keys).

Revision ID: 0015_packages
Revises: 0014
Create Date: 2026-10-27 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0015_packages'
down_revision: str | None = '0014'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _created_at() -> sa.Column:
    return sa.Column(
        'created_at',
        sa.DateTime(timezone=True),
        server_default=sa.text('(CURRENT_TIMESTAMP)'),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        'program_packages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.String(length=64), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('program_packages', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_program_packages_active'), ['active'], unique=False)

    op.create_table(
        'package_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('package_id', sa.Integer(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=True),
        sa.Column('kind', sa.String(length=16), nullable=False),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('telegram_file_id', sa.String(length=300), nullable=True),
        sa.Column('bale_file_id', sa.String(length=300), nullable=True),
        sa.Column('original_filename', sa.String(length=200), nullable=True),
        _created_at(),
        sa.ForeignKeyConstraint(['package_id'], ['program_packages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('package_items', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_package_items_package_id'), ['package_id'], unique=False
        )

    op.create_table(
        'package_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('package_id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.String(length=64), nullable=True),
        _created_at(),
        sa.ForeignKeyConstraint(['package_id'], ['program_packages.id']),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('package_id', 'person_id', name='uq_package_person'),
    )
    with op.batch_alter_table('package_assignments', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_package_assignments_active'), ['active'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_package_assignments_package_id'), ['package_id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_package_assignments_person_id'), ['person_id'], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table('package_assignments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_package_assignments_person_id'))
        batch_op.drop_index(batch_op.f('ix_package_assignments_package_id'))
        batch_op.drop_index(batch_op.f('ix_package_assignments_active'))
    op.drop_table('package_assignments')
    with op.batch_alter_table('package_items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_package_items_package_id'))
    op.drop_table('package_items')
    with op.batch_alter_table('program_packages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_program_packages_active'))
    op.drop_table('program_packages')
