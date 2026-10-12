"""add abha consents

P8-B02: `abha_consents` records each patient's consent (and later
revocation) to share health records through ABDM, per purpose.

Revision ID: e5b7c2d94a16
Revises: d4a2f6b8c901
Create Date: 2026-10-11 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e5b7c2d94a16'
down_revision: Union[str, None] = 'd4a2f6b8c901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'abha_consents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('purpose', sa.String(length=30), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('granted_by', sa.UUID(), nullable=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_by', sa.UUID(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_abha_consents_tenant_id_tenants')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_abha_consents_facility_id_facilities')),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_abha_consents_patient_id_patients')),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], name=op.f('fk_abha_consents_granted_by_users')),
        sa.ForeignKeyConstraint(['revoked_by'], ['users.id'], name=op.f('fk_abha_consents_revoked_by_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_abha_consents')),
    )
    op.create_index('ix_abha_consents_patient_id', 'abha_consents', ['patient_id'])


def downgrade() -> None:
    op.drop_index('ix_abha_consents_patient_id', table_name='abha_consents')
    op.drop_table('abha_consents')
