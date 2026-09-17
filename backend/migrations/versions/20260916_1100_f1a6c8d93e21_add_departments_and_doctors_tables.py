"""add departments and doctors tables

Adds the OPD Phase 3 master data schema: `departments` (facility-scoped,
unique `code` per facility) and `doctors` (facility-scoped, FK to
`departments`, optional FK to `users` for a doctor who is also a login).

Revision ID: f1a6c8d93e21
Revises: 7d2f9a41c6b3
Create Date: 2026-09-16 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f1a6c8d93e21'
down_revision: Union[str, None] = '7d2f9a41c6b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'departments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_departments_facility_id_facilities')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_departments_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_departments')),
        sa.UniqueConstraint('facility_id', 'code', name=op.f('uq_departments_facility_id_code')),
    )

    op.create_table(
        'doctors',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('department_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('doctor_code', sa.String(length=50), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('specialization', sa.String(length=255), nullable=False),
        sa.Column('qualification', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('consultation_fee', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], name=op.f('fk_doctors_department_id_departments')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_doctors_facility_id_facilities')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_doctors_tenant_id_tenants')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_doctors_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_doctors')),
        sa.UniqueConstraint('doctor_code', name=op.f('uq_doctors_doctor_code')),
    )
    op.create_index(op.f('ix_doctors_department_id'), 'doctors', ['department_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_doctors_department_id'), table_name='doctors')
    op.drop_table('doctors')
    op.drop_table('departments')
