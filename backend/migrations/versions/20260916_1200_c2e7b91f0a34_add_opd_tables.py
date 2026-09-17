"""add opd tables

Adds the OPD Phase 3 clinical schema (P3-B01): `opd_encounters` (the visit
record created by Registration, P3-F02), `opd_tokens` (the queue token for
an encounter - sequential per doctor per day; the live "queue" is a query
over this table, not a separate stored entity), and `opd_consultations` /
`opd_prescriptions` / `opd_prescription_items` (schema only for now - no
service/API until the consultation workflow ticket).

Revision ID: c2e7b91f0a34
Revises: d94b1f6c2a75
Create Date: 2026-09-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c2e7b91f0a34'
down_revision: Union[str, None] = 'd94b1f6c2a75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'opd_encounters',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('department_id', sa.UUID(), nullable=False),
        sa.Column('doctor_id', sa.UUID(), nullable=False),
        sa.Column('registered_by', sa.UUID(), nullable=True),
        sa.Column('encounter_number', sa.String(length=50), nullable=False),
        sa.Column('visit_type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], name=op.f('fk_opd_encounters_department_id_departments')),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], name=op.f('fk_opd_encounters_doctor_id_doctors')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_opd_encounters_facility_id_facilities')),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_opd_encounters_patient_id_patients')),
        sa.ForeignKeyConstraint(['registered_by'], ['users.id'], name=op.f('fk_opd_encounters_registered_by_users')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_opd_encounters_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_opd_encounters')),
        sa.UniqueConstraint('encounter_number', name=op.f('uq_opd_encounters_encounter_number')),
    )
    op.create_index(op.f('ix_opd_encounters_patient_id'), 'opd_encounters', ['patient_id'])
    op.create_index(op.f('ix_opd_encounters_doctor_id'), 'opd_encounters', ['doctor_id'])

    op.create_table(
        'opd_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('encounter_id', sa.UUID(), nullable=False),
        sa.Column('doctor_id', sa.UUID(), nullable=False),
        sa.Column('token_date', sa.Date(), nullable=False),
        sa.Column('token_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('called_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], name=op.f('fk_opd_tokens_doctor_id_doctors')),
        sa.ForeignKeyConstraint(['encounter_id'], ['opd_encounters.id'], name=op.f('fk_opd_tokens_encounter_id_opd_encounters')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_opd_tokens_facility_id_facilities')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_opd_tokens_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_opd_tokens')),
        sa.UniqueConstraint('encounter_id', name=op.f('uq_opd_tokens_encounter_id')),
        sa.UniqueConstraint('doctor_id', 'token_date', 'token_number', name=op.f('uq_opd_tokens_doctor_id_token_date_token_number')),
    )
    op.create_index(op.f('ix_opd_tokens_doctor_id_token_date'), 'opd_tokens', ['doctor_id', 'token_date'])

    op.create_table(
        'opd_consultations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('encounter_id', sa.UUID(), nullable=False),
        sa.Column('doctor_id', sa.UUID(), nullable=False),
        sa.Column('chief_complaint', sa.String(length=1000), nullable=True),
        sa.Column('diagnosis', sa.String(length=1000), nullable=True),
        sa.Column('clinical_notes', sa.String(length=2000), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['doctor_id'], ['doctors.id'], name=op.f('fk_opd_consultations_doctor_id_doctors')),
        sa.ForeignKeyConstraint(['encounter_id'], ['opd_encounters.id'], name=op.f('fk_opd_consultations_encounter_id_opd_encounters')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_opd_consultations_facility_id_facilities')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_opd_consultations_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_opd_consultations')),
        sa.UniqueConstraint('encounter_id', name=op.f('uq_opd_consultations_encounter_id')),
    )

    op.create_table(
        'opd_prescriptions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('consultation_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['consultation_id'], ['opd_consultations.id'], name=op.f('fk_opd_prescriptions_consultation_id_opd_consultations')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_opd_prescriptions_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_opd_prescriptions')),
    )
    op.create_index(op.f('ix_opd_prescriptions_consultation_id'), 'opd_prescriptions', ['consultation_id'])

    op.create_table(
        'opd_prescription_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('prescription_id', sa.UUID(), nullable=False),
        sa.Column('drug_name', sa.String(length=255), nullable=False),
        sa.Column('dosage', sa.String(length=100), nullable=True),
        sa.Column('frequency', sa.String(length=100), nullable=True),
        sa.Column('duration', sa.String(length=100), nullable=True),
        sa.Column('instructions', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['prescription_id'], ['opd_prescriptions.id'], name=op.f('fk_opd_prescription_items_prescription_id_opd_prescriptions')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_opd_prescription_items')),
    )
    op.create_index(op.f('ix_opd_prescription_items_prescription_id'), 'opd_prescription_items', ['prescription_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_opd_prescription_items_prescription_id'), table_name='opd_prescription_items')
    op.drop_table('opd_prescription_items')
    op.drop_index(op.f('ix_opd_prescriptions_consultation_id'), table_name='opd_prescriptions')
    op.drop_table('opd_prescriptions')
    op.drop_table('opd_consultations')
    op.drop_index(op.f('ix_opd_tokens_doctor_id_token_date'), table_name='opd_tokens')
    op.drop_table('opd_tokens')
    op.drop_index(op.f('ix_opd_encounters_doctor_id'), table_name='opd_encounters')
    op.drop_index(op.f('ix_opd_encounters_patient_id'), table_name='opd_encounters')
    op.drop_table('opd_encounters')
