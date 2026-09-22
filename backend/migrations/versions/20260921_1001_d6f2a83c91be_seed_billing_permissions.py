"""seed billing permissions

P5-B01: adds the `billing.view_services`, `billing.manage_services`,
`billing.view_invoices`, and `billing.refund` permission rows (the
`billing.create_invoice`/`billing.collect_payment` codes were already
seeded in 20260908_1005_..._seed_rbac_data_and_migrate_users.py, for
BILLING_CASHIER only - HOSPITAL_ADMIN's own gap in those two is fixed
later by 20260921_1401_a9c53f8e6b17_grant_hospital_admin_billing_invoice_and.py)
and grants each role the codes listed for it in `ROLE_PERMISSION_SEED` -
SUPER_ADMIN via `ALL_PERMISSION_CODES`, HOSPITAL_ADMIN and BILLING_CASHIER
get the new billing codes directly.

Revision ID: d6f2a83c91be
Revises: b8e1d4f927ac
Create Date: 2026-09-21 10:01:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd6f2a83c91be'
down_revision: Union[str, None] = 'b8e1d4f927ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (code, module, description) - a fixed snapshot of what P5-B01 needed, not
# a live import from app.modules.rbac.constants: that module has since been
# renamed/reshaped by later migrations (see
# 20260921_1400_b7f24a9c1d85_rename_billing_permissions.py), and a
# migration must keep working when replayed from scratch regardless of
# what the current code looks like.
NEW_PERMISSIONS = [
    ("billing.view_services", "billing", "View the service and package master catalog"),
    ("billing.manage_services", "billing", "Create and update services and packages"),
    ("billing.view_invoices", "billing", "View invoices, payments, deposits, and receipts"),
    ("billing.refund", "billing", "Refund payments and deposits"),
]
NEW_PERMISSION_CODES = [code for code, _, _ in NEW_PERMISSIONS]

# Which roles got which of the above, as ROLE_PERMISSION_SEED looked at the
# time this migration was authored (P5-B01) - SUPER_ADMIN via
# ALL_PERMISSION_CODES, HOSPITAL_ADMIN got all four, BILLING_CASHIER got
# only the two view permissions (`billing.create_invoice`/
# `billing.collect_payment` were seeded earlier, and it never had
# `billing.manage_services`/`billing.refund`).
ROLE_GRANTS = {
    "SUPER_ADMIN": NEW_PERMISSION_CODES,
    "HOSPITAL_ADMIN": NEW_PERMISSION_CODES,
    "BILLING_CASHIER": ["billing.view_services", "billing.view_invoices"],
}


def upgrade() -> None:
    connection = op.get_bind()

    permission_ids = {code: str(uuid.uuid4()) for code in NEW_PERMISSION_CODES}
    for code, module, description in NEW_PERMISSIONS:
        connection.execute(
            sa.text(
                """
                INSERT INTO permissions (id, code, module, description, created_at)
                VALUES (:id, :code, :module, :description, now())
                """
            ),
            {"id": permission_ids[code], "code": code, "module": module, "description": description},
        )

    role_rows = connection.execute(sa.text("SELECT id, code FROM roles")).mappings().all()
    role_ids_by_code = {row["code"]: str(row["id"]) for row in role_rows}

    for role_code, permission_codes in ROLE_GRANTS.items():
        role_id = role_ids_by_code.get(role_code)
        if role_id is None:
            continue
        for permission_code in permission_codes:
            connection.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :permission_id)"
                ),
                {"role_id": role_id, "permission_id": permission_ids[permission_code]},
            )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (SELECT id FROM permissions WHERE code = ANY(:codes))
            """
        ),
        {"codes": NEW_PERMISSION_CODES},
    )
    connection.execute(
        sa.text("DELETE FROM permissions WHERE code = ANY(:codes)"),
        {"codes": NEW_PERMISSION_CODES},
    )
