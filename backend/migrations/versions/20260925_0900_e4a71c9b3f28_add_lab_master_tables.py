"""add lab master tables

P6-F01: adds the Lab Master schema - `lab_tests` (MST-LAB-01),
`lab_parameters` (MST-PAR-01, one reportable analyte per test), and
`lab_reference_ranges` (a normal/critical band per parameter, scoped by
gender and an age band in days). Mirrors `app/modules/lab/models.py`
(written alongside the module's service/API/schema layer, but never
migrated - this fills that gap so the Lab Master frontend has real tables
to work against).

Only these three master tables are created here; the P6-B01 workflow
tables also defined in models.py (`lab_orders`, `lab_accessions`,
`lab_samples`, `lab_sample_status_history`, `lab_results`,
`lab_result_versions`, `lab_verifications`, `lab_approvals`) are left for
whichever migration lands alongside their own service/API work, per that
module's own docstring ("lands in a later phase").

Revision ID: e4a71c9b3f28
Revises: a9c53f8e6b17
Create Date: 2026-09-25 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e4a71c9b3f28'
down_revision: Union[str, None] = 'a9c53f8e6b17'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'lab_tests',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('department_id', sa.UUID(), nullable=True),
        sa.Column('test_code', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('specimen_type', sa.String(length=30), nullable=False),
        sa.Column('container_type', sa.String(length=30), nullable=False),
        sa.Column('tat_minutes', sa.Integer(), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], name=op.f('fk_lab_tests_department_id_departments')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_lab_tests_facility_id_facilities')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_lab_tests_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_lab_tests')),
        sa.UniqueConstraint('facility_id', 'test_code', name=op.f('uq_lab_tests_facility_id_test_code')),
    )

    op.create_table(
        'lab_parameters',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('test_id', sa.UUID(), nullable=False),
        sa.Column('parameter_code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_lab_parameters_facility_id_facilities')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_lab_parameters_tenant_id_tenants')),
        sa.ForeignKeyConstraint(['test_id'], ['lab_tests.id'], name=op.f('fk_lab_parameters_test_id_lab_tests')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_lab_parameters')),
        sa.UniqueConstraint('test_id', 'parameter_code', name=op.f('uq_lab_parameters_test_id_parameter_code')),
    )
    op.create_index(op.f('ix_lab_parameters_test_id'), 'lab_parameters', ['test_id'])

    op.create_table(
        'lab_reference_ranges',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('parameter_id', sa.UUID(), nullable=False),
        sa.Column('gender', sa.String(length=10), nullable=False),
        sa.Column('age_min_days', sa.Integer(), nullable=False),
        sa.Column('age_max_days', sa.Integer(), nullable=True),
        sa.Column('normal_min', sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column('normal_max', sa.Numeric(precision=12, scale=3), nullable=False),
        sa.Column('critical_low', sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column('critical_high', sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_lab_reference_ranges_facility_id_facilities')),
        sa.ForeignKeyConstraint(['parameter_id'], ['lab_parameters.id'], name=op.f('fk_lab_reference_ranges_parameter_id_lab_parameters')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_lab_reference_ranges_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_lab_reference_ranges')),
    )
    op.create_index(op.f('ix_lab_reference_ranges_parameter_id'), 'lab_reference_ranges', ['parameter_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_lab_reference_ranges_parameter_id'), table_name='lab_reference_ranges')
    op.drop_table('lab_reference_ranges')
    op.drop_index(op.f('ix_lab_parameters_test_id'), table_name='lab_parameters')
    op.drop_table('lab_parameters')
    op.drop_table('lab_tests')
