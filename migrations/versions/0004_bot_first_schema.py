"""bot-first schema: contact links, plan catalog, notifications, course terms

Transforms the v1 schema (post-0003) into the bot-first model:
  - class_types.key; channel_identities.username; courses.allowed_absence /
    travel_declared; attendance_events.created_by; payments.created_by
  - drops web-only persons.password_hash
  - introduces plan_types + plan_assignments and MIGRATES existing ``plans``
    rows into plan_assignments (data-preserving), then drops ``plans``
  - introduces contact_links and the unified notifications table

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-19 01:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Map the legacy ``plans.plan_type`` enum values to new plan_types.key values.
_ENUM_TO_KEY = {'NUTRITION': 'nutrition', 'TRAINING': 'training', 'CUSTOM': 'specialized'}
_KEY_TO_ENUM = {'nutrition': 'NUTRITION', 'training': 'TRAINING', 'specialized': 'CUSTOM'}
_DEFAULT_PLAN_TYPES = [
    {'key': 'nutrition', 'title': 'برنامه تغذیه اصولی', 'active': True, 'sort_order': 1},
    {'key': 'training', 'title': 'برنامه تمرینی اصولی', 'active': True, 'sort_order': 2},
    {'key': 'specialized', 'title': 'برنامه تمرینی تخصصی', 'active': True, 'sort_order': 3},
]


def _platform_enum(bind):
    """Reference the EXISTING ``platform`` enum without trying to recreate it."""
    if bind.dialect.name == 'postgresql':
        from sqlalchemy.dialects import postgresql

        return postgresql.ENUM('TELEGRAM', 'BALE', 'WEB', name='platform', create_type=False)
    return sa.Enum('TELEGRAM', 'BALE', 'WEB', name='platform')


def upgrade() -> None:
    bind = op.get_bind()
    platform_enum = _platform_enum(bind)

    # --- 1. class_types.key (backfilled, then unique NOT NULL) ---
    with op.batch_alter_table('class_types', schema=None) as batch_op:
        batch_op.add_column(sa.Column('key', sa.String(length=50), nullable=True))
    op.execute("UPDATE class_types SET key = 'class-' || id WHERE key IS NULL")
    with op.batch_alter_table('class_types', schema=None) as batch_op:
        batch_op.alter_column('key', existing_type=sa.String(length=50), nullable=False)
        batch_op.create_index(batch_op.f('ix_class_types_key'), ['key'], unique=True)

    # --- 2. channel_identities.username ---
    with op.batch_alter_table('channel_identities', schema=None) as batch_op:
        batch_op.add_column(sa.Column('username', sa.String(length=100), nullable=True))

    # --- 3. courses: locked attendance terms ---
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('allowed_absence', sa.Integer(), nullable=False, server_default='0')
        )
        batch_op.add_column(
            sa.Column('travel_declared', sa.Boolean(), nullable=False, server_default=sa.false())
        )

    # --- 4. audit columns ---
    with op.batch_alter_table('attendance_events', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_by', sa.String(length=64), nullable=True))
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_by', sa.String(length=64), nullable=True))

    # --- 5. drop web-only password hash ---
    with op.batch_alter_table('persons', schema=None) as batch_op:
        batch_op.drop_column('password_hash')

    # --- 6. plan catalog ---
    op.create_table(
        'plan_types',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('plan_types', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_plan_types_active'), ['active'], unique=False)
        batch_op.create_index(batch_op.f('ix_plan_types_key'), ['key'], unique=True)

    plan_types_tbl = sa.table(
        'plan_types',
        sa.column('key', sa.String),
        sa.column('title', sa.String),
        sa.column('active', sa.Boolean),
        sa.column('sort_order', sa.Integer),
    )
    op.bulk_insert(plan_types_tbl, _DEFAULT_PLAN_TYPES)

    # --- 7. plan_assignments ---
    op.create_table(
        'plan_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=False),
        sa.Column('plan_type_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('coach_note', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(length=300), nullable=True),
        sa.Column('original_filename', sa.String(length=200), nullable=True),
        sa.Column('platform_file_id', sa.String(length=300), nullable=True),
        sa.Column('file_platform', platform_enum, nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.String(length=64), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id']),
        sa.ForeignKeyConstraint(['plan_type_id'], ['plan_types.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('plan_assignments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_plan_assignments_active'), ['active'], unique=False)
        batch_op.create_index(
            batch_op.f('ix_plan_assignments_person_id'), ['person_id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_plan_assignments_plan_type_id'), ['plan_type_id'], unique=False
        )

    # --- 8. migrate plans -> plan_assignments (data-preserving) ---
    inspector = sa.inspect(bind)
    if 'plans' in inspector.get_table_names():
        type_ids = dict(bind.execute(sa.text("SELECT key, id FROM plan_types")).fetchall())
        default_type_id = type_ids.get('specialized') or next(iter(type_ids.values()))
        rows = (
            bind.execute(
                sa.text(
                    "SELECT person_id, plan_type, title, description, file_path, "
                    "original_filename, active, created_at FROM plans"
                )
            )
            .mappings()
            .all()
        )
        insert_stmt = sa.text(
            "INSERT INTO plan_assignments "
            "(person_id, plan_type_id, title, coach_note, file_path, "
            " original_filename, active, created_at) "
            "VALUES (:person_id, :plan_type_id, :title, :coach_note, :file_path, "
            " :original_filename, :active, :created_at)"
        )
        for row in rows:
            key = _ENUM_TO_KEY.get(row['plan_type'], 'specialized')
            bind.execute(
                insert_stmt,
                {
                    'person_id': row['person_id'],
                    'plan_type_id': type_ids.get(key, default_type_id),
                    'title': row['title'],
                    'coach_note': row['description'],
                    'file_path': row['file_path'],
                    'original_filename': row['original_filename'],
                    'active': row['active'],
                    'created_at': row['created_at'],
                },
            )
        with op.batch_alter_table('plans', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_plans_person_id'))
            batch_op.drop_index(batch_op.f('ix_plans_active'))
        op.drop_table('plans')
        if bind.dialect.name == 'postgresql':
            sa.Enum(name='plantype').drop(bind, checkfirst=True)

    # --- 9. contact_links ---
    op.create_table(
        'contact_links',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=50), nullable=False),
        sa.Column('label', sa.String(length=100), nullable=False),
        sa.Column('url', sa.String(length=500), nullable=False),
        sa.Column('icon', sa.String(length=16), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('platform', platform_enum, nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('contact_links', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_contact_links_active'), ['active'], unique=False)
        batch_op.create_index(batch_op.f('ix_contact_links_key'), ['key'], unique=True)

    # --- 10. unified notifications ---
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=True),
        sa.Column(
            'kind',
            sa.Enum(
                'LOW_SESSIONS', 'COURSE_ENDING', 'PAYMENT_REMINDER', 'NEW_PLAN',
                'ATTENDANCE', 'MANUAL', 'BROADCAST', name='notificationkind',
            ),
            nullable=False,
        ),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'SENT', 'FAILED', 'CANCELLED', name='notificationstatus'),
            nullable=False,
        ),
        sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.String(length=500), nullable=True),
        sa.Column('idempotency_key', sa.String(length=200), nullable=True),
        sa.Column('created_by', sa.String(length=64), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key', name='uq_notifications_idempotency_key'),
    )
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_notifications_person_id'), ['person_id'], unique=False
        )
        batch_op.create_index(batch_op.f('ix_notifications_status'), ['status'], unique=False)
        batch_op.create_index(
            'ix_notifications_status_scheduled', ['status', 'scheduled_for'], unique=False
        )


def downgrade() -> None:
    bind = op.get_bind()

    # notifications
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.drop_index('ix_notifications_status_scheduled')
        batch_op.drop_index(batch_op.f('ix_notifications_status'))
        batch_op.drop_index(batch_op.f('ix_notifications_person_id'))
    op.drop_table('notifications')
    if bind.dialect.name == 'postgresql':
        sa.Enum(name='notificationkind').drop(bind, checkfirst=True)
        sa.Enum(name='notificationstatus').drop(bind, checkfirst=True)

    # contact_links
    with op.batch_alter_table('contact_links', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_contact_links_key'))
        batch_op.drop_index(batch_op.f('ix_contact_links_active'))
    op.drop_table('contact_links')

    # recreate plans + plantype enum, copy assignments back (best-effort)
    plantype = sa.Enum('TRAINING', 'NUTRITION', 'CUSTOM', name='plantype')
    if bind.dialect.name == 'postgresql':
        plantype.create(bind, checkfirst=True)
        plantype = sa.Enum(
            'TRAINING', 'NUTRITION', 'CUSTOM', name='plantype', create_type=False
        )
    op.create_table(
        'plans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('person_id', sa.Integer(), nullable=False),
        sa.Column('plan_type', plantype, nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(length=300), nullable=True),
        sa.Column('original_filename', sa.String(length=200), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(['person_id'], ['persons.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('plans', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_plans_active'), ['active'], unique=False)
        batch_op.create_index(batch_op.f('ix_plans_person_id'), ['person_id'], unique=False)

    rows = (
        bind.execute(
            sa.text(
                "SELECT pa.person_id, pt.key AS type_key, pa.title, pa.coach_note, "
                "pa.file_path, pa.original_filename, pa.active, pa.created_at "
                "FROM plan_assignments pa JOIN plan_types pt ON pt.id = pa.plan_type_id"
            )
        )
        .mappings()
        .all()
    )
    insert_stmt = sa.text(
        "INSERT INTO plans "
        "(person_id, plan_type, title, description, file_path, "
        " original_filename, active, created_at) "
        "VALUES (:person_id, :plan_type, :title, :description, :file_path, "
        " :original_filename, :active, :created_at)"
    )
    for row in rows:
        bind.execute(
            insert_stmt,
            {
                'person_id': row['person_id'],
                'plan_type': _KEY_TO_ENUM.get(row['type_key'], 'CUSTOM'),
                'title': row['title'] or '-',
                'description': row['coach_note'],
                'file_path': row['file_path'],
                'original_filename': row['original_filename'],
                'active': row['active'],
                'created_at': row['created_at'],
            },
        )

    with op.batch_alter_table('plan_assignments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_plan_assignments_plan_type_id'))
        batch_op.drop_index(batch_op.f('ix_plan_assignments_person_id'))
        batch_op.drop_index(batch_op.f('ix_plan_assignments_active'))
    op.drop_table('plan_assignments')
    with op.batch_alter_table('plan_types', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_plan_types_key'))
        batch_op.drop_index(batch_op.f('ix_plan_types_active'))
    op.drop_table('plan_types')

    # restore web-only password hash
    with op.batch_alter_table('persons', schema=None) as batch_op:
        batch_op.add_column(sa.Column('password_hash', sa.String(length=255), nullable=True))

    # drop audit / course / identity / class_type additions
    with op.batch_alter_table('payments', schema=None) as batch_op:
        batch_op.drop_column('created_by')
    with op.batch_alter_table('attendance_events', schema=None) as batch_op:
        batch_op.drop_column('created_by')
    with op.batch_alter_table('courses', schema=None) as batch_op:
        batch_op.drop_column('travel_declared')
        batch_op.drop_column('allowed_absence')
    with op.batch_alter_table('channel_identities', schema=None) as batch_op:
        batch_op.drop_column('username')
    with op.batch_alter_table('class_types', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_class_types_key'))
        batch_op.drop_column('key')
