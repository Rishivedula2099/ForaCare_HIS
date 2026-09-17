"""add token priority

Adds `opd_tokens.priority` (P3-B02) - NORMAL or PRIORITY, used to order the
doctor's queue (priority tokens surface ahead of normal ones; see
`app/modules/opd/service.py::get_doctor_queue`).

Revision ID: b5f8a1d4c672
Revises: e6a4d2c8f150
Create Date: 2026-09-16 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b5f8a1d4c672'
down_revision: Union[str, None] = 'e6a4d2c8f150'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'opd_tokens',
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='NORMAL'),
    )
    op.alter_column('opd_tokens', 'priority', server_default=None)


def downgrade() -> None:
    op.drop_column('opd_tokens', 'priority')
