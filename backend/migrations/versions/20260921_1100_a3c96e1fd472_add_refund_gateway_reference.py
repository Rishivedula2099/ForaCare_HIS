"""add refund gateway reference

P5-B04: adds `billing_refunds.gateway_reference`, populated from
`PaymentAdapter.process_refund`'s `transaction_reference`
(app/modules/billing/payment_adapter.py) - a `MockPaymentAdapter` reference
today, a real gateway's refund ID once a production adapter exists.

Revision ID: a3c96e1fd472
Revises: d6f2a83c91be
Create Date: 2026-09-21 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a3c96e1fd472'
down_revision: Union[str, None] = 'd6f2a83c91be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('billing_refunds', sa.Column('gateway_reference', sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column('billing_refunds', 'gateway_reference')
