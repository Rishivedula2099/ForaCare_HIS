"""grant full billing access to all roles except super admin

Opens the Billing & Cashier module to every role except SUPER_ADMIN (which
already has every permission via `ALL_PERMISSION_CODES`) and, per the
S5-B01 refund restriction, BILLING_CASHIER keeps its existing scope
unchanged. Grants DOCTOR, NURSE, RECEPTIONIST, LAB_TECH, LAB_APPROVER, and
AUDITOR the full billing permission set (`_FULL_BILLING_ACCESS` in
app/modules/rbac/constants.py): view services/invoices, manage the
service/package catalog, create invoices, collect payments, and refund.

Revision ID: c4e8f19a7d63
Revises: f6d3a8b45c92
Create Date: 2026-09-21 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c4e8f19a7d63'
down_revision: Union[str, None] = 'f6d3a8b45c92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FULL_BILLING_ACCESS = [
    "billing.view_services",
    "billing.manage_services",
    "billing.view_invoices",
    "billing.create_invoice",
    "billing.collect_payment",
    "billing.refund",
]

GRANTED_ROLE_CODES = ["DOCTOR", "NURSE", "RECEPTIONIST", "LAB_TECH", "LAB_APPROVER", "AUDITOR"]


def upgrade() -> None:
    connection = op.get_bind()

    role_rows = connection.execute(
        sa.text("SELECT id, code FROM roles WHERE code = ANY(:codes)"), {"codes": GRANTED_ROLE_CODES}
    ).mappings().all()
    role_ids_by_code = {row["code"]: str(row["id"]) for row in role_rows}

    permission_rows = connection.execute(
        sa.text("SELECT id, code FROM permissions WHERE code = ANY(:codes)"), {"codes": FULL_BILLING_ACCESS}
    ).mappings().all()
    permission_ids_by_code = {row["code"]: str(row["id"]) for row in permission_rows}

    for role_code in GRANTED_ROLE_CODES:
        role_id = role_ids_by_code.get(role_code)
        if role_id is None:
            continue
        for permission_code in FULL_BILLING_ACCESS:
            permission_id = permission_ids_by_code.get(permission_code)
            if permission_id is None:
                continue
            connection.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT :role_id, :permission_id
                    WHERE NOT EXISTS (
                        SELECT 1 FROM role_permissions
                        WHERE role_id = :role_id AND permission_id = :permission_id
                    )
                    """
                ),
                {"role_id": role_id, "permission_id": permission_id},
            )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE role_id IN (SELECT id FROM roles WHERE code = ANY(:role_codes))
              AND permission_id IN (SELECT id FROM permissions WHERE code = ANY(:permission_codes))
            """
        ),
        {"role_codes": GRANTED_ROLE_CODES, "permission_codes": FULL_BILLING_ACCESS},
    )
