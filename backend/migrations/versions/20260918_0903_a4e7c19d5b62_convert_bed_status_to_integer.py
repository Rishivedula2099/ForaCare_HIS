"""convert bed status to integer

P4-B02: `ipd_beds.status` moves from a free-form VARCHAR label to a small
integer code (see BED_STATUS_CODES/BED_STATUS_LABELS in
app/modules/ipd/models.py) - the API/service layer and frontend are
unaffected, they still speak the string label; only the DB column and the
ORM's raw attribute (renamed `status_code`) are numeric.

Revision ID: a4e7c19d5b62
Revises: f83c5a1e6d92
Create Date: 2026-09-18 09:03:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a4e7c19d5b62'
down_revision: Union[str, None] = 'f83c5a1e6d92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LABEL_TO_CODE_SQL = """
    CASE status
        WHEN 'AVAILABLE' THEN 1
        WHEN 'RESERVED' THEN 2
        WHEN 'OCCUPIED' THEN 3
        WHEN 'CLEANING' THEN 4
        WHEN 'MAINTENANCE' THEN 5
        WHEN 'BLOCKED' THEN 6
    END
"""

_CODE_TO_LABEL_SQL = """
    CASE status_code
        WHEN 1 THEN 'AVAILABLE'
        WHEN 2 THEN 'RESERVED'
        WHEN 3 THEN 'OCCUPIED'
        WHEN 4 THEN 'CLEANING'
        WHEN 5 THEN 'MAINTENANCE'
        WHEN 6 THEN 'BLOCKED'
    END
"""


def upgrade() -> None:
    op.alter_column(
        'ipd_beds',
        'status',
        existing_type=sa.String(length=20),
        type_=sa.Integer(),
        postgresql_using=_LABEL_TO_CODE_SQL.strip(),
    )
    op.alter_column('ipd_beds', 'status', new_column_name='status_code', existing_type=sa.Integer())


def downgrade() -> None:
    op.alter_column('ipd_beds', 'status_code', new_column_name='status', existing_type=sa.Integer())
    op.alter_column(
        'ipd_beds',
        'status',
        existing_type=sa.Integer(),
        type_=sa.String(length=20),
        postgresql_using=_CODE_TO_LABEL_SQL.strip(),
    )
