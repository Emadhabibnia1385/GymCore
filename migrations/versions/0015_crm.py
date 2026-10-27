"""add leads, person_notes and follow_ups («📇 پیگیری‌ها»)

The coach had nothing to follow up with: who should renew, who asked about
classes but never registered, what was said. Three new tables, nothing
existing changes:

- `leads` — someone who asked but is not a student yet; `person_id` is set
  once they are converted (and cleared if that student is ever deleted).
- `person_notes` — a student's timeline of what was said, append-only.
- `follow_ups` — "contact this student / lead on that day"; exactly one of
  `person_id` / `lead_id` is set (ck_follow_ups_one_target).

`source` and `status` are VARCHAR rather than native enums, so a later value
needs no ALTER TYPE.

Revision ID: 0015_crm
Revises: 0014
Create Date: 2026-10-27 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '0015_crm'
down_revision: str | None = '0014'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _created_at(name: str = 'created_at') -> sa.Column:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        server_default=sa.text('(CURRENT_TIMESTAMP)'),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        'leads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False, server_default='OTHER'),
        sa.Column('interest', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='NEW'),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('next_follow_up', sa.Date(), nullable=True),
        sa.Column('person_id', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.String(length=64), nullable=True),
        _created_at(),
        _created_at('updated_at'),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('leads', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_leads_person_id'), ['person_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_leads_phone'), ['phone'], unique=False)
        batch_op.create_index(batch_op.f('ix_leads_status'), ['status'], unique=False)

    op.create_table(
        'person_notes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('created_by', sa.String(length=64), nullable=True),
        _created_at(),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('person_notes', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_person_notes_person_id'), ['person_id'], unique=False
        )

    op.create_table(
        'follow_ups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=True),
        sa.Column('lead_id', sa.Integer(), nullable=True),
        sa.Column('due_on', sa.Date(), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('done', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('done_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(length=64), nullable=True),
        _created_at(),
        sa.CheckConstraint(
            '(person_id IS NULL) <> (lead_id IS NULL)', name='ck_follow_ups_one_target'
        ),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('follow_ups', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_follow_ups_done'), ['done'], unique=False)
        batch_op.create_index(batch_op.f('ix_follow_ups_due_on'), ['due_on'], unique=False)
        batch_op.create_index(batch_op.f('ix_follow_ups_lead_id'), ['lead_id'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_follow_ups_person_id'), ['person_id'], unique=False
        )


def downgrade() -> None:
    # Dependents first: follow_ups references leads.
    with op.batch_alter_table('follow_ups', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_follow_ups_person_id'))
        batch_op.drop_index(batch_op.f('ix_follow_ups_lead_id'))
        batch_op.drop_index(batch_op.f('ix_follow_ups_due_on'))
        batch_op.drop_index(batch_op.f('ix_follow_ups_done'))
    op.drop_table('follow_ups')

    with op.batch_alter_table('person_notes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_person_notes_person_id'))
    op.drop_table('person_notes')

    with op.batch_alter_table('leads', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_leads_status'))
        batch_op.drop_index(batch_op.f('ix_leads_phone'))
        batch_op.drop_index(batch_op.f('ix_leads_person_id'))
    op.drop_table('leads')
