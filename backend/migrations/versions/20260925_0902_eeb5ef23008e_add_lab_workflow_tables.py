"""add lab workflow tables

P6-B01/P6-B02: adds the downstream half of the Lab Database - `lab_orders`,
`lab_accessions`, `lab_samples`, `lab_sample_status_history`, `lab_results`,
`lab_result_versions`, `lab_verifications`, `lab_approvals`, and
`lab_order_status_history`, backing the P6-B02 order-level state machine
(`ORDERED -> BILLED -> ACCESSIONED -> COLLECTION_PENDING -> COLLECTED ->
PROCESSING -> RESULT_ENTERED -> TECHNICALLY_VERIFIED -> PENDING_APPROVAL ->
APPROVED -> FINALIZED`, with `CANCELLED` reachable from any non-terminal
state - see `app/modules/lab/service.LAB_ORDER_TRANSITIONS`). Accessioning/
result-entry screens land in a later phase (P6-F02+); see
app/modules/lab/models.py for the per-table rationale.

`lab_orders` and `lab_accessions` reference each other (an order is folded
into an accession once billed; an accession's samples serve one or more
orders), so `lab_accessions` is created first with `lab_orders.accession_id`
added as a nullable FK afterwards - avoids a circular `create_table`
dependency without a deferred/ALTER-added constraint on both sides.

Revision ID: eeb5ef23008e
Revises: f28d6c4a91be
Create Date: 2026-09-25 09:02:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'eeb5ef23008e'
down_revision: Union[str, None] = 'f28d6c4a91be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'lab_accessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('accessioned_by', sa.UUID(), nullable=True),
        sa.Column('accession_number', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('accessioned_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['accessioned_by'], ['users.id'], name=op.f('fk_lab_accessions_accessioned_by_users')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_lab_accessions_facility_id_facilities')),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_lab_accessions_patient_id_patients')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_lab_accessions_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_lab_accessions')),
        sa.UniqueConstraint('accession_number', name=op.f('uq_lab_accessions_accession_number')),
    )
    op.create_index(op.f('ix_lab_accessions_patient_id'), 'lab_accessions', ['patient_id'])

    op.create_table(
        'lab_orders',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('test_id', sa.UUID(), nullable=False),
        sa.Column('encounter_id', sa.UUID(), nullable=True),
        sa.Column('admission_id', sa.UUID(), nullable=True),
        sa.Column('ordered_by', sa.UUID(), nullable=True),
        sa.Column('invoice_item_id', sa.UUID(), nullable=True),
        sa.Column('accession_id', sa.UUID(), nullable=True),
        sa.Column('order_number', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('clinical_notes', sa.String(length=500), nullable=True),
        sa.Column('ordered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['accession_id'], ['lab_accessions.id'], name=op.f('fk_lab_orders_accession_id_lab_accessions')),
        sa.ForeignKeyConstraint(['admission_id'], ['ipd_admissions.id'], name=op.f('fk_lab_orders_admission_id_ipd_admissions')),
        sa.ForeignKeyConstraint(['encounter_id'], ['opd_encounters.id'], name=op.f('fk_lab_orders_encounter_id_opd_encounters')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_lab_orders_facility_id_facilities')),
        sa.ForeignKeyConstraint(['invoice_item_id'], ['billing_invoice_items.id'], name=op.f('fk_lab_orders_invoice_item_id_billing_invoice_items')),
        sa.ForeignKeyConstraint(['ordered_by'], ['doctors.id'], name=op.f('fk_lab_orders_ordered_by_doctors')),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_lab_orders_patient_id_patients')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_lab_orders_tenant_id_tenants')),
        sa.ForeignKeyConstraint(['test_id'], ['lab_tests.id'], name=op.f('fk_lab_orders_test_id_lab_tests')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_lab_orders')),
        sa.UniqueConstraint('order_number', name=op.f('uq_lab_orders_order_number')),
    )
    op.create_index(op.f('ix_lab_orders_patient_id'), 'lab_orders', ['patient_id'])
    op.create_index(op.f('ix_lab_orders_accession_id'), 'lab_orders', ['accession_id'])
    op.create_index(op.f('ix_lab_orders_status'), 'lab_orders', ['status'])

    op.create_table(
        'lab_order_status_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('lab_order_id', sa.UUID(), nullable=False),
        sa.Column('changed_by', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('remarks', sa.String(length=500), nullable=True),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], name=op.f('fk_lab_order_status_history_changed_by_users')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_lab_order_status_history_facility_id_facilities')),
        sa.ForeignKeyConstraint(['lab_order_id'], ['lab_orders.id'], name=op.f('fk_lab_order_status_history_lab_order_id_lab_orders')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_lab_order_status_history_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_lab_order_status_history')),
    )
    op.create_index(op.f('ix_lab_order_status_history_lab_order_id'), 'lab_order_status_history', ['lab_order_id'])

    op.create_table(
        'lab_samples',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('accession_id', sa.UUID(), nullable=False),
        sa.Column('collected_by', sa.UUID(), nullable=True),
        sa.Column('barcode_id', sa.String(length=50), nullable=False),
        sa.Column('specimen_type', sa.String(length=30), nullable=False),
        sa.Column('container_type', sa.String(length=30), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('rejection_reason', sa.String(length=500), nullable=True),
        sa.Column('collected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['accession_id'], ['lab_accessions.id'], name=op.f('fk_lab_samples_accession_id_lab_accessions')),
        sa.ForeignKeyConstraint(['collected_by'], ['users.id'], name=op.f('fk_lab_samples_collected_by_users')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_lab_samples_facility_id_facilities')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_lab_samples_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_lab_samples')),
        sa.UniqueConstraint('barcode_id', name=op.f('uq_lab_samples_barcode_id')),
    )
    op.create_index(op.f('ix_lab_samples_accession_id'), 'lab_samples', ['accession_id'])

    op.create_table(
        'lab_sample_status_history',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('sample_id', sa.UUID(), nullable=False),
        sa.Column('changed_by', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('remarks', sa.String(length=500), nullable=True),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], name=op.f('fk_lab_sample_status_history_changed_by_users')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_lab_sample_status_history_facility_id_facilities')),
        sa.ForeignKeyConstraint(['sample_id'], ['lab_samples.id'], name=op.f('fk_lab_sample_status_history_sample_id_lab_samples')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_lab_sample_status_history_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_lab_sample_status_history')),
    )
    op.create_index(op.f('ix_lab_sample_status_history_sample_id'), 'lab_sample_status_history', ['sample_id'])

    op.create_table(
        'lab_results',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('lab_order_id', sa.UUID(), nullable=False),
        sa.Column('parameter_id', sa.UUID(), nullable=False),
        sa.Column('sample_id', sa.UUID(), nullable=True),
        sa.Column('entered_by', sa.UUID(), nullable=True),
        sa.Column('value', sa.String(length=100), nullable=False),
        sa.Column('unit', sa.String(length=50), nullable=True),
        sa.Column('flag', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('current_version', sa.Integer(), nullable=False),
        sa.Column('entered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['entered_by'], ['users.id'], name=op.f('fk_lab_results_entered_by_users')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_lab_results_facility_id_facilities')),
        sa.ForeignKeyConstraint(['lab_order_id'], ['lab_orders.id'], name=op.f('fk_lab_results_lab_order_id_lab_orders')),
        sa.ForeignKeyConstraint(['parameter_id'], ['lab_parameters.id'], name=op.f('fk_lab_results_parameter_id_lab_parameters')),
        sa.ForeignKeyConstraint(['sample_id'], ['lab_samples.id'], name=op.f('fk_lab_results_sample_id_lab_samples')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_lab_results_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_lab_results')),
        sa.UniqueConstraint('lab_order_id', 'parameter_id', name=op.f('uq_lab_results_order_id_parameter_id')),
    )
    op.create_index(op.f('ix_lab_results_lab_order_id'), 'lab_results', ['lab_order_id'])

    op.create_table(
        'lab_result_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('result_id', sa.UUID(), nullable=False),
        sa.Column('changed_by', sa.UUID(), nullable=True),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('value', sa.String(length=100), nullable=False),
        sa.Column('flag', sa.String(length=20), nullable=False),
        sa.Column('change_reason', sa.String(length=500), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], name=op.f('fk_lab_result_versions_changed_by_users')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_lab_result_versions_facility_id_facilities')),
        sa.ForeignKeyConstraint(['result_id'], ['lab_results.id'], name=op.f('fk_lab_result_versions_result_id_lab_results')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_lab_result_versions_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_lab_result_versions')),
        sa.UniqueConstraint('result_id', 'version_number', name=op.f('uq_lab_result_versions_result_id_version')),
    )
    op.create_index(op.f('ix_lab_result_versions_result_id'), 'lab_result_versions', ['result_id'])

    op.create_table(
        'lab_verifications',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('lab_order_id', sa.UUID(), nullable=False),
        sa.Column('verified_by', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('remarks', sa.String(length=500), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_lab_verifications_facility_id_facilities')),
        sa.ForeignKeyConstraint(['lab_order_id'], ['lab_orders.id'], name=op.f('fk_lab_verifications_lab_order_id_lab_orders')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_lab_verifications_tenant_id_tenants')),
        sa.ForeignKeyConstraint(['verified_by'], ['users.id'], name=op.f('fk_lab_verifications_verified_by_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_lab_verifications')),
    )
    op.create_index(op.f('ix_lab_verifications_lab_order_id'), 'lab_verifications', ['lab_order_id'])

    op.create_table(
        'lab_approvals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('lab_order_id', sa.UUID(), nullable=False),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('remarks', sa.String(length=500), nullable=True),
        sa.Column('report_checksum', sa.String(length=128), nullable=True),
        sa.Column('report_qr_token', sa.String(length=128), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], name=op.f('fk_lab_approvals_approved_by_users')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_lab_approvals_facility_id_facilities')),
        sa.ForeignKeyConstraint(['lab_order_id'], ['lab_orders.id'], name=op.f('fk_lab_approvals_lab_order_id_lab_orders')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_lab_approvals_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_lab_approvals')),
    )
    op.create_index(op.f('ix_lab_approvals_lab_order_id'), 'lab_approvals', ['lab_order_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_lab_approvals_lab_order_id'), table_name='lab_approvals')
    op.drop_table('lab_approvals')
    op.drop_index(op.f('ix_lab_verifications_lab_order_id'), table_name='lab_verifications')
    op.drop_table('lab_verifications')
    op.drop_index(op.f('ix_lab_result_versions_result_id'), table_name='lab_result_versions')
    op.drop_table('lab_result_versions')
    op.drop_index(op.f('ix_lab_results_lab_order_id'), table_name='lab_results')
    op.drop_table('lab_results')
    op.drop_index(op.f('ix_lab_sample_status_history_sample_id'), table_name='lab_sample_status_history')
    op.drop_table('lab_sample_status_history')
    op.drop_index(op.f('ix_lab_samples_accession_id'), table_name='lab_samples')
    op.drop_table('lab_samples')
    op.drop_index(op.f('ix_lab_order_status_history_lab_order_id'), table_name='lab_order_status_history')
    op.drop_table('lab_order_status_history')
    op.drop_index(op.f('ix_lab_orders_status'), table_name='lab_orders')
    op.drop_index(op.f('ix_lab_orders_accession_id'), table_name='lab_orders')
    op.drop_index(op.f('ix_lab_orders_patient_id'), table_name='lab_orders')
    op.drop_table('lab_orders')
    op.drop_index(op.f('ix_lab_accessions_patient_id'), table_name='lab_accessions')
    op.drop_table('lab_accessions')
