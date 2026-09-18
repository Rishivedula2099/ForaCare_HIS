"""add ipd tables

Adds the Phase 4 IPD schema (P4-B01): `ipd_wards`, `ipd_rooms`, `ipd_beds`
(the Ward/Room/Bed master data behind P4-F01's bed board), plus
`ipd_admissions`, `ipd_bed_assignments`, `ipd_transfers`, `ipd_consents`,
and `ipd_discharges` so later tickets (admission/transfer/discharge/consent
workflows) can build on a stable schema without further migrations.

Revision ID: c1d4e8a53f67
Revises: e5b9d3c48a71
Create Date: 2026-09-18 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c1d4e8a53f67'
down_revision: Union[str, None] = 'e5b9d3c48a71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ipd_wards',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('department_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('ward_type', sa.String(length=20), nullable=False),
        sa.Column('floor', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], name=op.f('fk_ipd_wards_department_id_departments')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_ipd_wards_facility_id_facilities')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_ipd_wards_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ipd_wards')),
        sa.UniqueConstraint('facility_id', 'code', name=op.f('uq_ipd_wards_facility_id_code')),
    )

    op.create_table(
        'ipd_rooms',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('ward_id', sa.UUID(), nullable=False),
        sa.Column('room_number', sa.String(length=20), nullable=False),
        sa.Column('room_type', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_ipd_rooms_facility_id_facilities')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_ipd_rooms_tenant_id_tenants')),
        sa.ForeignKeyConstraint(['ward_id'], ['ipd_wards.id'], name=op.f('fk_ipd_rooms_ward_id_ipd_wards')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ipd_rooms')),
        sa.UniqueConstraint('ward_id', 'room_number', name=op.f('uq_ipd_rooms_ward_id_room_number')),
    )
    op.create_index(op.f('ix_ipd_rooms_ward_id'), 'ipd_rooms', ['ward_id'])

    op.create_table(
        'ipd_beds',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('ward_id', sa.UUID(), nullable=False),
        sa.Column('room_id', sa.UUID(), nullable=False),
        sa.Column('bed_number', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_ipd_beds_facility_id_facilities')),
        sa.ForeignKeyConstraint(['room_id'], ['ipd_rooms.id'], name=op.f('fk_ipd_beds_room_id_ipd_rooms')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_ipd_beds_tenant_id_tenants')),
        sa.ForeignKeyConstraint(['ward_id'], ['ipd_wards.id'], name=op.f('fk_ipd_beds_ward_id_ipd_wards')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ipd_beds')),
        sa.UniqueConstraint('room_id', 'bed_number', name=op.f('uq_ipd_beds_room_id_bed_number')),
    )
    op.create_index(op.f('ix_ipd_beds_ward_id'), 'ipd_beds', ['ward_id'])
    op.create_index(op.f('ix_ipd_beds_room_id'), 'ipd_beds', ['room_id'])
    op.create_index(op.f('ix_ipd_beds_status'), 'ipd_beds', ['status'])

    op.create_table(
        'ipd_admissions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('admitting_doctor_id', sa.UUID(), nullable=True),
        sa.Column('department_id', sa.UUID(), nullable=True),
        sa.Column('admitted_by', sa.UUID(), nullable=True),
        sa.Column('admission_number', sa.String(length=50), nullable=False),
        sa.Column('admission_type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('notes', sa.String(length=1000), nullable=True),
        sa.Column('admitted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admitting_doctor_id'], ['doctors.id'], name=op.f('fk_ipd_admissions_admitting_doctor_id_doctors')),
        sa.ForeignKeyConstraint(['admitted_by'], ['users.id'], name=op.f('fk_ipd_admissions_admitted_by_users')),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], name=op.f('fk_ipd_admissions_department_id_departments')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_ipd_admissions_facility_id_facilities')),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_ipd_admissions_patient_id_patients')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_ipd_admissions_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ipd_admissions')),
        sa.UniqueConstraint('admission_number', name=op.f('uq_ipd_admissions_admission_number')),
    )
    op.create_index(op.f('ix_ipd_admissions_patient_id'), 'ipd_admissions', ['patient_id'])
    op.create_index(op.f('ix_ipd_admissions_status'), 'ipd_admissions', ['status'])

    op.create_table(
        'ipd_bed_assignments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('admission_id', sa.UUID(), nullable=False),
        sa.Column('bed_id', sa.UUID(), nullable=False),
        sa.Column('assigned_by', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['admission_id'], ['ipd_admissions.id'], name=op.f('fk_ipd_bed_assignments_admission_id_ipd_admissions')),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], name=op.f('fk_ipd_bed_assignments_assigned_by_users')),
        sa.ForeignKeyConstraint(['bed_id'], ['ipd_beds.id'], name=op.f('fk_ipd_bed_assignments_bed_id_ipd_beds')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_ipd_bed_assignments_facility_id_facilities')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_ipd_bed_assignments_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ipd_bed_assignments')),
    )
    op.create_index(op.f('ix_ipd_bed_assignments_admission_id'), 'ipd_bed_assignments', ['admission_id'])
    op.create_index(op.f('ix_ipd_bed_assignments_bed_id'), 'ipd_bed_assignments', ['bed_id'])
    op.create_index(op.f('ix_ipd_bed_assignments_status'), 'ipd_bed_assignments', ['status'])

    op.create_table(
        'ipd_transfers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('admission_id', sa.UUID(), nullable=False),
        sa.Column('from_bed_id', sa.UUID(), nullable=True),
        sa.Column('to_bed_id', sa.UUID(), nullable=False),
        sa.Column('transferred_by', sa.UUID(), nullable=True),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.Column('transferred_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admission_id'], ['ipd_admissions.id'], name=op.f('fk_ipd_transfers_admission_id_ipd_admissions')),
        sa.ForeignKeyConstraint(['from_bed_id'], ['ipd_beds.id'], name=op.f('fk_ipd_transfers_from_bed_id_ipd_beds')),
        sa.ForeignKeyConstraint(['to_bed_id'], ['ipd_beds.id'], name=op.f('fk_ipd_transfers_to_bed_id_ipd_beds')),
        sa.ForeignKeyConstraint(['transferred_by'], ['users.id'], name=op.f('fk_ipd_transfers_transferred_by_users')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_ipd_transfers_facility_id_facilities')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_ipd_transfers_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ipd_transfers')),
    )
    op.create_index(op.f('ix_ipd_transfers_admission_id'), 'ipd_transfers', ['admission_id'])

    op.create_table(
        'ipd_consents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('admission_id', sa.UUID(), nullable=False),
        sa.Column('recorded_by', sa.UUID(), nullable=True),
        sa.Column('consent_type', sa.String(length=30), nullable=False),
        sa.Column('consent_given', sa.Boolean(), nullable=False),
        sa.Column('given_by_name', sa.String(length=255), nullable=False),
        sa.Column('relationship_to_patient', sa.String(length=50), nullable=True),
        sa.Column('notes', sa.String(length=1000), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admission_id'], ['ipd_admissions.id'], name=op.f('fk_ipd_consents_admission_id_ipd_admissions')),
        sa.ForeignKeyConstraint(['recorded_by'], ['users.id'], name=op.f('fk_ipd_consents_recorded_by_users')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_ipd_consents_facility_id_facilities')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_ipd_consents_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ipd_consents')),
    )
    op.create_index(op.f('ix_ipd_consents_admission_id'), 'ipd_consents', ['admission_id'])

    op.create_table(
        'ipd_discharges',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('admission_id', sa.UUID(), nullable=False),
        sa.Column('discharged_by', sa.UUID(), nullable=True),
        sa.Column('discharge_type', sa.String(length=20), nullable=False),
        sa.Column('discharge_condition', sa.String(length=50), nullable=True),
        sa.Column('discharge_summary', sa.String(length=2000), nullable=True),
        sa.Column('follow_up_instructions', sa.String(length=1000), nullable=True),
        sa.Column('discharged_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admission_id'], ['ipd_admissions.id'], name=op.f('fk_ipd_discharges_admission_id_ipd_admissions')),
        sa.ForeignKeyConstraint(['discharged_by'], ['users.id'], name=op.f('fk_ipd_discharges_discharged_by_users')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_ipd_discharges_facility_id_facilities')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_ipd_discharges_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ipd_discharges')),
        sa.UniqueConstraint('admission_id', name=op.f('uq_ipd_discharges_admission_id')),
    )


def downgrade() -> None:
    op.drop_table('ipd_discharges')
    op.drop_index(op.f('ix_ipd_consents_admission_id'), table_name='ipd_consents')
    op.drop_table('ipd_consents')
    op.drop_index(op.f('ix_ipd_transfers_admission_id'), table_name='ipd_transfers')
    op.drop_table('ipd_transfers')
    op.drop_index(op.f('ix_ipd_bed_assignments_status'), table_name='ipd_bed_assignments')
    op.drop_index(op.f('ix_ipd_bed_assignments_bed_id'), table_name='ipd_bed_assignments')
    op.drop_index(op.f('ix_ipd_bed_assignments_admission_id'), table_name='ipd_bed_assignments')
    op.drop_table('ipd_bed_assignments')
    op.drop_index(op.f('ix_ipd_admissions_status'), table_name='ipd_admissions')
    op.drop_index(op.f('ix_ipd_admissions_patient_id'), table_name='ipd_admissions')
    op.drop_table('ipd_admissions')
    op.drop_index(op.f('ix_ipd_beds_status'), table_name='ipd_beds')
    op.drop_index(op.f('ix_ipd_beds_room_id'), table_name='ipd_beds')
    op.drop_index(op.f('ix_ipd_beds_ward_id'), table_name='ipd_beds')
    op.drop_table('ipd_beds')
    op.drop_index(op.f('ix_ipd_rooms_ward_id'), table_name='ipd_rooms')
    op.drop_table('ipd_rooms')
    op.drop_table('ipd_wards')
