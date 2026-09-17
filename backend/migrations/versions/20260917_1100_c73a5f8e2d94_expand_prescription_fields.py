"""expand prescription fields

Expands the prescription schema (P3-F06/P3-B05): `opd_prescriptions` gets
`facility_id`/`doctor_id` (denormalized from the consultation so isolation/
authorization checks don't need a join) and `updated_at`, plus a unique
constraint on `consultation_id` (one prescription per consultation).
`opd_prescription_items` gets a required `route` column and `dosage`/
`frequency`/`duration` become required (they were optional placeholders
from the P3-B01 schema-only pass).

Revision ID: c73a5f8e2d94
Revises: b2e7f4a91c58
Create Date: 2026-09-17 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c73a5f8e2d94'
down_revision: Union[str, None] = 'b2e7f4a91c58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()

    # --- opd_prescriptions ---
    op.add_column('opd_prescriptions', sa.Column('facility_id', sa.UUID(), nullable=True))
    op.add_column('opd_prescriptions', sa.Column('doctor_id', sa.UUID(), nullable=True))
    op.add_column(
        'opd_prescriptions',
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.alter_column('opd_prescriptions', 'updated_at', server_default=None)

    # Backfill from the linked consultation (no real rows expected yet - this
    # is defensive, matching the pattern used for prior schema-only tables).
    connection.execute(
        sa.text(
            """
            UPDATE opd_prescriptions p
            SET facility_id = c.facility_id, doctor_id = c.doctor_id
            FROM opd_consultations c
            WHERE c.id = p.consultation_id AND (p.facility_id IS NULL OR p.doctor_id IS NULL)
            """
        )
    )
    op.alter_column('opd_prescriptions', 'facility_id', nullable=False)
    op.alter_column('opd_prescriptions', 'doctor_id', nullable=False)

    op.create_foreign_key(
        op.f('fk_opd_prescriptions_facility_id_facilities'), 'opd_prescriptions', 'facilities', ['facility_id'], ['id']
    )
    op.create_foreign_key(
        op.f('fk_opd_prescriptions_doctor_id_doctors'), 'opd_prescriptions', 'doctors', ['doctor_id'], ['id']
    )
    op.create_unique_constraint(
        op.f('uq_opd_prescriptions_consultation_id'), 'opd_prescriptions', ['consultation_id']
    )

    # --- opd_prescription_items ---
    op.add_column(
        'opd_prescription_items',
        sa.Column('route', sa.String(length=30), nullable=False, server_default='ORAL'),
    )
    op.alter_column('opd_prescription_items', 'route', server_default=None)

    connection.execute(sa.text("UPDATE opd_prescription_items SET dosage = '' WHERE dosage IS NULL"))
    connection.execute(sa.text("UPDATE opd_prescription_items SET frequency = '' WHERE frequency IS NULL"))
    connection.execute(sa.text("UPDATE opd_prescription_items SET duration = '' WHERE duration IS NULL"))
    op.alter_column('opd_prescription_items', 'dosage', nullable=False)
    op.alter_column('opd_prescription_items', 'frequency', nullable=False)
    op.alter_column('opd_prescription_items', 'duration', nullable=False)

    op.add_column(
        'opd_prescription_items',
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.alter_column('opd_prescription_items', 'created_at', server_default=None)


def downgrade() -> None:
    op.drop_column('opd_prescription_items', 'created_at')
    op.alter_column('opd_prescription_items', 'duration', nullable=True)
    op.alter_column('opd_prescription_items', 'frequency', nullable=True)
    op.alter_column('opd_prescription_items', 'dosage', nullable=True)
    op.drop_column('opd_prescription_items', 'route')

    op.drop_constraint(op.f('uq_opd_prescriptions_consultation_id'), 'opd_prescriptions', type_='unique')
    op.drop_constraint(op.f('fk_opd_prescriptions_doctor_id_doctors'), 'opd_prescriptions', type_='foreignkey')
    op.drop_constraint(op.f('fk_opd_prescriptions_facility_id_facilities'), 'opd_prescriptions', type_='foreignkey')
    op.drop_column('opd_prescriptions', 'updated_at')
    op.drop_column('opd_prescriptions', 'doctor_id')
    op.drop_column('opd_prescriptions', 'facility_id')
