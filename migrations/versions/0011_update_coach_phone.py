"""update the coach's contact phone to 09152050950

Content refresh for existing deployments: the phone and WhatsApp contact
links carry the old number, and seeding only fills in MISSING keys, so the
rows have to be updated here. Fresh installs get the same values from
services/contact_links.py::_DEFAULT_LINKS.

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-07 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = '0011'
down_revision: str | None = '0010'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD = "09305560950"
_NEW = "09152050950"
_OLD_INTL = "989305560950"
_NEW_INTL = "989152050950"


def upgrade() -> None:
    op.execute(
        "UPDATE contact_links "
        f"SET label = 'تلفن: {_NEW}', url = 'tel:{_NEW}' "
        "WHERE key = 'phone'"
    )
    op.execute(
        "UPDATE contact_links "
        f"SET label = 'واتساپ: {_NEW}', url = 'https://wa.me/{_NEW_INTL}' "
        "WHERE key = 'whatsapp'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE contact_links "
        f"SET label = 'تلفن: {_OLD}', url = 'tel:{_OLD}' "
        "WHERE key = 'phone'"
    )
    op.execute(
        "UPDATE contact_links "
        f"SET label = 'واتساپ: {_OLD}', url = 'https://wa.me/{_OLD_INTL}' "
        "WHERE key = 'whatsapp'"
    )
