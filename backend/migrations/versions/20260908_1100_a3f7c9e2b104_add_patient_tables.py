"""add patient master tables

Adds the Patient Master schema for Phase 2 (P2-B01): `patients` plus its
child tables `patient_addresses`, `patient_contacts`, `patient_photos`,
`patient_identifiers`, and `patient_identity_links` (external identity
links such as ABHA, kept separate so the internal UID stays the durable
primary identifier - see context.md Multi-Hospital Architecture).

Revision ID: a3f7c9e2b104
Revises: e7c1f4a2b856
Create Date: 2026-09-08 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a3f7c9e2b104'
down_revision: Union[str, None] = 'e7c1f4a2b856'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'patients',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('uid', sa.String(length=50), nullable=False),
        sa.Column('mrn', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=20), nullable=True),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('middle_name', sa.String(length=100), nullable=True),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('gender', sa.String(length=20), nullable=False),
        sa.Column('dob', sa.Date(), nullable=False),
        sa.Column('blood_group', sa.String(length=20), nullable=False),
        sa.Column('marital_status', sa.String(length=20), nullable=True),
        sa.Column('occupation', sa.String(length=100), nullable=True),
        sa.Column('preferred_language', sa.String(length=50), nullable=True),
        sa.Column('is_minor', sa.Boolean(), nullable=False),
        sa.Column('guardian_name', sa.String(length=255), nullable=True),
        sa.Column('guardian_relationship', sa.String(length=30), nullable=True),
        sa.Column('guardian_phone', sa.String(length=20), nullable=True),
        sa.Column('guardian_address', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('registered_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_patients_facility_id_facilities')),
        sa.ForeignKeyConstraint(['registered_by'], ['users.id'], name=op.f('fk_patients_registered_by_users')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_patients_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_patients')),
        sa.UniqueConstraint('mrn', name=op.f('uq_patients_mrn')),
        sa.UniqueConstraint('uid', name=op.f('uq_patients_uid')),
    )

    op.create_table(
        'patient_addresses',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('address_type', sa.String(length=20), nullable=False),
        sa.Column('street', sa.String(length=500), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('pincode', sa.String(length=10), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_patient_addresses_patient_id_patients')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_patient_addresses')),
        sa.UniqueConstraint('patient_id', name=op.f('uq_patient_addresses_patient_id')),
    )

    op.create_table(
        'patient_contacts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('contact_type', sa.String(length=20), nullable=False),
        sa.Column('value', sa.String(length=255), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_patient_contacts_patient_id_patients')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_patient_contacts')),
    )

    op.create_table(
        'patient_photos',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_patient_photos_patient_id_patients')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_patient_photos')),
    )

    op.create_table(
        'patient_identifiers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('identity_type', sa.String(length=30), nullable=False),
        sa.Column('id_number', sa.String(length=100), nullable=False),
        sa.Column('is_verified', sa.Boolean(), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_patient_identifiers_patient_id_patients')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_patient_identifiers')),
    )

    op.create_table(
        'patient_identity_links',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('system', sa.String(length=30), nullable=False),
        sa.Column('external_id', sa.String(length=100), nullable=True),
        sa.Column('external_address', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('linked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_patient_identity_links_patient_id_patients')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_patient_identity_links')),
    )


def downgrade() -> None:
    op.drop_table('patient_identity_links')
    op.drop_table('patient_identifiers')
    op.drop_table('patient_photos')
    op.drop_table('patient_contacts')
    op.drop_table('patient_addresses')
    op.drop_table('patients')
