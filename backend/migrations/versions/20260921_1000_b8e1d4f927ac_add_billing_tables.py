"""add billing tables

P5-B01: adds the Phase 5 financial database - `billing_services` and
`billing_packages` (the Service/Package master behind P5-F01), plus
`billing_invoices`/`billing_invoice_items`, `billing_deposits`,
`billing_payments`, `billing_refunds`, and `billing_receipts`. Payments,
deposits, and refunds are append-only ledgers (see `Deposit`/`Payment`/
`Refund` in app/modules/billing/models.py), the same pattern as
`ipd_deposits`; `billing_invoices` carries mutable running totals
(`amount_paid`/`amount_due`/`status`) that `app/modules/billing/service.py`
keeps in sync with those ledger rows.

Revision ID: b8e1d4f927ac
Revises: 43f5e8c76abf
Create Date: 2026-09-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b8e1d4f927ac'
down_revision: Union[str, None] = '43f5e8c76abf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'billing_services',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('department_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('category', sa.String(length=30), nullable=False),
        sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], name=op.f('fk_billing_services_department_id_departments')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_billing_services_facility_id_facilities')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_billing_services_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_billing_services')),
        sa.UniqueConstraint('facility_id', 'code', name=op.f('uq_billing_services_facility_id_code')),
    )

    op.create_table(
        'billing_packages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_billing_packages_facility_id_facilities')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_billing_packages_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_billing_packages')),
        sa.UniqueConstraint('facility_id', 'code', name=op.f('uq_billing_packages_facility_id_code')),
    )

    op.create_table(
        'billing_invoices',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('admission_id', sa.UUID(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('subtotal', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('discount_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('amount_paid', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('amount_due', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('notes', sa.String(length=1000), nullable=True),
        sa.Column('invoice_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admission_id'], ['ipd_admissions.id'], name=op.f('fk_billing_invoices_admission_id_ipd_admissions')),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_billing_invoices_created_by_users')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_billing_invoices_facility_id_facilities')),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_billing_invoices_patient_id_patients')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_billing_invoices_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_billing_invoices')),
        sa.UniqueConstraint('invoice_number', name=op.f('uq_billing_invoices_invoice_number')),
    )
    op.create_index(op.f('ix_billing_invoices_patient_id'), 'billing_invoices', ['patient_id'])
    op.create_index(op.f('ix_billing_invoices_status'), 'billing_invoices', ['status'])

    op.create_table(
        'billing_invoice_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('invoice_id', sa.UUID(), nullable=False),
        sa.Column('service_id', sa.UUID(), nullable=True),
        sa.Column('package_id', sa.UUID(), nullable=True),
        sa.Column('item_type', sa.String(length=20), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('discount_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_billing_invoice_items_facility_id_facilities')),
        sa.ForeignKeyConstraint(['invoice_id'], ['billing_invoices.id'], name=op.f('fk_billing_invoice_items_invoice_id_billing_invoices')),
        sa.ForeignKeyConstraint(['package_id'], ['billing_packages.id'], name=op.f('fk_billing_invoice_items_package_id_billing_packages')),
        sa.ForeignKeyConstraint(['service_id'], ['billing_services.id'], name=op.f('fk_billing_invoice_items_service_id_billing_services')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_billing_invoice_items_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_billing_invoice_items')),
    )
    op.create_index(op.f('ix_billing_invoice_items_invoice_id'), 'billing_invoice_items', ['invoice_id'])

    op.create_table(
        'billing_deposits',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('admission_id', sa.UUID(), nullable=True),
        sa.Column('received_by', sa.UUID(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('payment_mode', sa.String(length=20), nullable=False),
        sa.Column('reference_number', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admission_id'], ['ipd_admissions.id'], name=op.f('fk_billing_deposits_admission_id_ipd_admissions')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_billing_deposits_facility_id_facilities')),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_billing_deposits_patient_id_patients')),
        sa.ForeignKeyConstraint(['received_by'], ['users.id'], name=op.f('fk_billing_deposits_received_by_users')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_billing_deposits_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_billing_deposits')),
    )
    op.create_index(op.f('ix_billing_deposits_patient_id'), 'billing_deposits', ['patient_id'])

    op.create_table(
        'billing_payments',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('invoice_id', sa.UUID(), nullable=False),
        sa.Column('received_by', sa.UUID(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('payment_mode', sa.String(length=20), nullable=False),
        sa.Column('reference_number', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_billing_payments_facility_id_facilities')),
        sa.ForeignKeyConstraint(['invoice_id'], ['billing_invoices.id'], name=op.f('fk_billing_payments_invoice_id_billing_invoices')),
        sa.ForeignKeyConstraint(['received_by'], ['users.id'], name=op.f('fk_billing_payments_received_by_users')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_billing_payments_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_billing_payments')),
    )
    op.create_index(op.f('ix_billing_payments_invoice_id'), 'billing_payments', ['invoice_id'])

    op.create_table(
        'billing_refunds',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('payment_id', sa.UUID(), nullable=True),
        sa.Column('deposit_id', sa.UUID(), nullable=True),
        sa.Column('processed_by', sa.UUID(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('reason', sa.String(length=500), nullable=False),
        sa.Column('refund_mode', sa.String(length=20), nullable=False),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['deposit_id'], ['billing_deposits.id'], name=op.f('fk_billing_refunds_deposit_id_billing_deposits')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_billing_refunds_facility_id_facilities')),
        sa.ForeignKeyConstraint(['payment_id'], ['billing_payments.id'], name=op.f('fk_billing_refunds_payment_id_billing_payments')),
        sa.ForeignKeyConstraint(['processed_by'], ['users.id'], name=op.f('fk_billing_refunds_processed_by_users')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_billing_refunds_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_billing_refunds')),
    )

    op.create_table(
        'billing_receipts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('patient_id', sa.UUID(), nullable=False),
        sa.Column('payment_id', sa.UUID(), nullable=True),
        sa.Column('deposit_id', sa.UUID(), nullable=True),
        sa.Column('refund_id', sa.UUID(), nullable=True),
        sa.Column('issued_by', sa.UUID(), nullable=True),
        sa.Column('receipt_number', sa.String(length=50), nullable=False),
        sa.Column('receipt_type', sa.String(length=20), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['deposit_id'], ['billing_deposits.id'], name=op.f('fk_billing_receipts_deposit_id_billing_deposits')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_billing_receipts_facility_id_facilities')),
        sa.ForeignKeyConstraint(['issued_by'], ['users.id'], name=op.f('fk_billing_receipts_issued_by_users')),
        sa.ForeignKeyConstraint(['patient_id'], ['patients.id'], name=op.f('fk_billing_receipts_patient_id_patients')),
        sa.ForeignKeyConstraint(['payment_id'], ['billing_payments.id'], name=op.f('fk_billing_receipts_payment_id_billing_payments')),
        sa.ForeignKeyConstraint(['refund_id'], ['billing_refunds.id'], name=op.f('fk_billing_receipts_refund_id_billing_refunds')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_billing_receipts_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_billing_receipts')),
        sa.UniqueConstraint('receipt_number', name=op.f('uq_billing_receipts_receipt_number')),
    )
    op.create_index(op.f('ix_billing_receipts_patient_id'), 'billing_receipts', ['patient_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_billing_receipts_patient_id'), table_name='billing_receipts')
    op.drop_table('billing_receipts')
    op.drop_table('billing_refunds')
    op.drop_index(op.f('ix_billing_payments_invoice_id'), table_name='billing_payments')
    op.drop_table('billing_payments')
    op.drop_index(op.f('ix_billing_deposits_patient_id'), table_name='billing_deposits')
    op.drop_table('billing_deposits')
    op.drop_index(op.f('ix_billing_invoice_items_invoice_id'), table_name='billing_invoice_items')
    op.drop_table('billing_invoice_items')
    op.drop_index(op.f('ix_billing_invoices_status'), table_name='billing_invoices')
    op.drop_index(op.f('ix_billing_invoices_patient_id'), table_name='billing_invoices')
    op.drop_table('billing_invoices')
    op.drop_table('billing_packages')
    op.drop_table('billing_services')
