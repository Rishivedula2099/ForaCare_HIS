"""add encounter qr fields

Adds the P3-F04 check-in QR fields to `opd_encounters`: `qr_code` (opaque,
unique - not the encounter id itself, so a QR can't be forged by
enumeration), `qr_status` (ACTIVE/REVOKED), and `qr_revoked_at`. Expiry is
derived (end of the registration day) rather than stored - see
`OPDEncounter.qr_expires_at` in app/modules/opd/models.py.

Existing rows (local/dev only) are backfilled with an md5-based value
before the column is made NOT NULL + unique.

Revision ID: a19d7e5f3b28
Revises: b5f8a1d4c672
Create Date: 2026-09-16 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a19d7e5f3b28'
down_revision: Union[str, None] = 'b5f8a1d4c672'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('opd_encounters', sa.Column('qr_code', sa.String(length=64), nullable=True))
    op.add_column(
        'opd_encounters',
        sa.Column('qr_status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
    )
    op.add_column('opd_encounters', sa.Column('qr_revoked_at', sa.DateTime(timezone=True), nullable=True))

    op.execute(
        "UPDATE opd_encounters SET qr_code = md5(id::text || clock_timestamp()::text) WHERE qr_code IS NULL"
    )

    op.alter_column('opd_encounters', 'qr_code', nullable=False)
    op.alter_column('opd_encounters', 'qr_status', server_default=None)
    op.create_unique_constraint(op.f('uq_opd_encounters_qr_code'), 'opd_encounters', ['qr_code'])


def downgrade() -> None:
    op.drop_constraint(op.f('uq_opd_encounters_qr_code'), 'opd_encounters', type_='unique')
    op.drop_column('opd_encounters', 'qr_revoked_at')
    op.drop_column('opd_encounters', 'qr_status')
    op.drop_column('opd_encounters', 'qr_code')
