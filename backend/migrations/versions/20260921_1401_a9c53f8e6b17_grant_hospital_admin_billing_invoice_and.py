"""grant hospital admin billing.invoice.create and billing.payment.create

Fixes a gap dating back to the original P5-B01 seed migration
(20260921_1001_d6f2a83c91be_seed_billing_permissions.py), which assumed
HOSPITAL_ADMIN already held `billing.create_invoice`/`billing.collect_payment`
"from the base RBAC seed" - it never actually did; only BILLING_CASHIER did.
As a result HOSPITAL_ADMIN could view the billing module (`billing.view`)
and refund (`billing.refund.create`) but not create invoices or collect
payments, contradicting the required authorization model (HOSPITAL_ADMIN
must hold all four billing permissions).

Revision ID: a9c53f8e6b17
Revises: b7f24a9c1d85
Create Date: 2026-09-21 14:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a9c53f8e6b17'
down_revision: Union[str, None] = 'b7f24a9c1d85'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

MISSING_CODES = ["billing.invoice.create", "billing.payment.create"]


def upgrade() -> None:
    connection = op.get_bind()
    for code in MISSING_CODES:
        connection.execute(
            sa.text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT r.id, p.id
                FROM roles r, permissions p
                WHERE r.code = 'HOSPITAL_ADMIN' AND p.code = :code
                AND NOT EXISTS (
                    SELECT 1 FROM role_permissions existing
                    WHERE existing.role_id = r.id AND existing.permission_id = p.id
                )
                """
            ),
            {"code": code},
        )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE role_id = (SELECT id FROM roles WHERE code = 'HOSPITAL_ADMIN')
              AND permission_id IN (SELECT id FROM permissions WHERE code = ANY(:codes))
            """
        ),
        {"codes": MISSING_CODES},
    )
