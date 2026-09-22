"""revoke cashier refund permission

S5-B01: refund authority is restricted to HOSPITAL_ADMIN/SUPER_ADMIN by
default (see `ROLE_PERMISSION_SEED[SystemRole.BILLING_CASHIER]` in
app/modules/rbac/constants.py) - a cashier can collect payments and
deposits but not reverse them. Removes the `billing.refund` grant seeded
onto BILLING_CASHIER by 20260921_1001_..._seed_billing_permissions.py.

Revision ID: e9b4c7a2f318
Revises: a3c96e1fd472
Create Date: 2026-09-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e9b4c7a2f318'
down_revision: Union[str, None] = 'a3c96e1fd472'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE role_id = (SELECT id FROM roles WHERE code = 'BILLING_CASHIER')
              AND permission_id = (SELECT id FROM permissions WHERE code = 'billing.refund')
            """
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT (SELECT id FROM roles WHERE code = 'BILLING_CASHIER'),
                   (SELECT id FROM permissions WHERE code = 'billing.refund')
            WHERE NOT EXISTS (
                SELECT 1 FROM role_permissions
                WHERE role_id = (SELECT id FROM roles WHERE code = 'BILLING_CASHIER')
                  AND permission_id = (SELECT id FROM permissions WHERE code = 'billing.refund')
            )
            """
        )
    )
