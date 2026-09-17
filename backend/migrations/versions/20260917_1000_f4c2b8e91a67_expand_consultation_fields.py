"""expand consultation fields

Expands `opd_consultations` (P3-F05/P3-B04) with the full set of OPD
consultation sections - history, examination, allergies, investigation,
treatment, plus a fixed structured vitals block (temperature, pulse, BP,
SpO2, respiratory rate, weight, height) - and a `status` column
(IN_PROGRESS/COMPLETED). `clinical_notes` is renamed to `notes` to match
the "Notes" section name used everywhere else (API, UI).

Revision ID: f4c2b8e91a67
Revises: a19d7e5f3b28
Create Date: 2026-09-17 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f4c2b8e91a67'
down_revision: Union[str, None] = 'a19d7e5f3b28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('opd_consultations', 'clinical_notes', new_column_name='notes')

    op.add_column(
        'opd_consultations',
        sa.Column('status', sa.String(length=20), nullable=False, server_default='IN_PROGRESS'),
    )
    op.alter_column('opd_consultations', 'status', server_default=None)

    op.add_column('opd_consultations', sa.Column('history', sa.String(length=2000), nullable=True))
    op.add_column('opd_consultations', sa.Column('examination', sa.String(length=2000), nullable=True))
    op.add_column('opd_consultations', sa.Column('allergies', sa.String(length=1000), nullable=True))
    op.add_column('opd_consultations', sa.Column('investigation', sa.String(length=1000), nullable=True))
    op.add_column('opd_consultations', sa.Column('treatment', sa.String(length=2000), nullable=True))

    op.add_column('opd_consultations', sa.Column('temperature_celsius', sa.Numeric(precision=4, scale=1), nullable=True))
    op.add_column('opd_consultations', sa.Column('pulse_bpm', sa.Integer(), nullable=True))
    op.add_column('opd_consultations', sa.Column('bp_systolic', sa.Integer(), nullable=True))
    op.add_column('opd_consultations', sa.Column('bp_diastolic', sa.Integer(), nullable=True))
    op.add_column('opd_consultations', sa.Column('spo2_percent', sa.Integer(), nullable=True))
    op.add_column('opd_consultations', sa.Column('respiratory_rate', sa.Integer(), nullable=True))
    op.add_column('opd_consultations', sa.Column('weight_kg', sa.Numeric(precision=5, scale=1), nullable=True))
    op.add_column('opd_consultations', sa.Column('height_cm', sa.Numeric(precision=5, scale=1), nullable=True))


def downgrade() -> None:
    op.drop_column('opd_consultations', 'height_cm')
    op.drop_column('opd_consultations', 'weight_kg')
    op.drop_column('opd_consultations', 'respiratory_rate')
    op.drop_column('opd_consultations', 'spo2_percent')
    op.drop_column('opd_consultations', 'bp_diastolic')
    op.drop_column('opd_consultations', 'bp_systolic')
    op.drop_column('opd_consultations', 'pulse_bpm')
    op.drop_column('opd_consultations', 'temperature_celsius')

    op.drop_column('opd_consultations', 'treatment')
    op.drop_column('opd_consultations', 'investigation')
    op.drop_column('opd_consultations', 'allergies')
    op.drop_column('opd_consultations', 'examination')
    op.drop_column('opd_consultations', 'history')

    op.drop_column('opd_consultations', 'status')

    op.alter_column('opd_consultations', 'notes', new_column_name='clinical_notes')
