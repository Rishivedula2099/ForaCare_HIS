"""add billing idempotency keys

P5-B05: adds `billing_idempotency_keys`, storing the outcome of a financial
mutation submitted with an `Idempotency-Key` header keyed by
(tenant_id, scope, idempotency_key) - see `IdempotencyKey` in
app/modules/billing/models.py and `_check_idempotency`/`_save_idempotency`
in app/modules/billing/service.py.

Revision ID: f6d3a8b45c92
Revises: e9b4c7a2f318
Create Date: 2026-09-21 12:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f6d3a8b45c92'
down_revision: Union[str, None] = 'e9b4c7a2f318'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'billing_idempotency_keys',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('scope', sa.String(length=50), nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('request_hash', sa.String(length=64), nullable=False),
        sa.Column('response_body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_billing_idempotency_keys_facility_id_facilities')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_billing_idempotency_keys_tenant_id_tenants')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_billing_idempotency_keys')),
        sa.UniqueConstraint('tenant_id', 'scope', 'idempotency_key', name='uq_billing_idempotency_scope_key'),
    )


def downgrade() -> None:
    op.drop_table('billing_idempotency_keys')
