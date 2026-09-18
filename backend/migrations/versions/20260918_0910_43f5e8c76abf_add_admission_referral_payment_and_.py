"""add admission referral, payment category, and deposits

P4-F03/P4-B04: extends `ipd_admissions` with `referral_source`/
`referral_detail` (how the patient reached the facility) and
`payment_category` (billing category chosen at admission time), and adds
`ipd_deposits` as an append-only ledger of deposit payments recorded
against an admission (`create_admission`/`create_deposit` in
app/modules/ipd/service.py), rather than a single mutable deposit amount,
so multiple deposits over the course of a stay are each auditable.

Revision ID: 43f5e8c76abf
Revises: a4e7c19d5b62
Create Date: 2026-09-18 09:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '43f5e8c76abf'
down_revision: Union[str, None] = 'a4e7c19d5b62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'ipd_admissions',
        sa.Column('referral_source', sa.String(length=20), nullable=False, server_default='SELF'),
    )
    op.alter_column('ipd_admissions', 'referral_source', server_default=None)
    op.add_column('ipd_admissions', sa.Column('referral_detail', sa.String(length=255), nullable=True))
    op.add_column(
        'ipd_admissions',
        sa.Column('payment_category', sa.String(length=20), nullable=False, server_default='CASH'),
    )
    op.alter_column('ipd_admissions', 'payment_category', server_default=None)

    op.create_table(
        'ipd_deposits',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('admission_id', sa.UUID(), nullable=False),
        sa.Column('received_by', sa.UUID(), nullable=True),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('payment_mode', sa.String(length=20), nullable=False),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['admission_id'], ['ipd_admissions.id'], name=op.f('fk_ipd_deposits_admission_id_ipd_admissions')),
        sa.ForeignKeyConstraint(['received_by'], ['users.id'], name=op.f('fk_ipd_deposits_received_by_users')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_ipd_deposits_facility_id_facilities')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_ipd_deposits_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_ipd_deposits')),
    )
    op.create_index(op.f('ix_ipd_deposits_admission_id'), 'ipd_deposits', ['admission_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_ipd_deposits_admission_id'), table_name='ipd_deposits')
    op.drop_table('ipd_deposits')

    op.drop_column('ipd_admissions', 'payment_category')
    op.drop_column('ipd_admissions', 'referral_detail')
    op.drop_column('ipd_admissions', 'referral_source')
