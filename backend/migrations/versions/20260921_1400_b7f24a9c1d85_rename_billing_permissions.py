"""rename billing permissions to view/invoice.create/payment.create/refund.create

Fixes the Billing module's authorization model: MODULE ACCESS (can the
Billing page be opened at all) is now a single `billing.view` permission,
separate from per-action authority. Previously two view permissions
(`billing.view_services`, `billing.view_invoices`) each gated only half of
the module's read endpoints, so a role missing either one - as
HOSPITAL_ADMIN and BILLING_CASHIER both were, after the P5-B01 permission
seed and later grants drifted apart from what the frontend actually
called - could hit a 403 on some page-load query and get redirected to
/forbidden even though "the billing module" conceptually should have been
open to them.

Renames (old -> new), consolidating the two view permissions into one:
  billing.view_services  -> billing.view
  billing.view_invoices  -> billing.view
  billing.create_invoice -> billing.invoice.create
  billing.collect_payment -> billing.payment.create
  billing.refund          -> billing.refund.create
`billing.manage_services` is unchanged (it already meant something distinct
from module access: managing the service/package catalog).

Every role holding any of the old codes is granted the corresponding new
code; the old permission rows (and their role grants) are then removed.

Revision ID: b7f24a9c1d85
Revises: c4e8f19a7d63
Create Date: 2026-09-21 14:00:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b7f24a9c1d85'
down_revision: Union[str, None] = 'c4e8f19a7d63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (old_code, new_code, new_description)
RENAMES = [
    ("billing.view_services", "billing.view", "View the billing module - services, packages, invoices, payments, deposits, and receipts"),
    ("billing.view_invoices", "billing.view", "View the billing module - services, packages, invoices, payments, deposits, and receipts"),
    ("billing.create_invoice", "billing.invoice.create", "Create invoices and add line items"),
    ("billing.collect_payment", "billing.payment.create", "Collect payments and deposits"),
    ("billing.refund", "billing.refund.create", "Refund payments and deposits"),
]
OLD_CODES = [old for old, _, _ in RENAMES]
NEW_CODES = sorted({new for _, new, _ in RENAMES})


def upgrade() -> None:
    connection = op.get_bind()

    # 1. Insert the new permission rows (billing.view is inserted once even
    #    though two old codes map to it).
    new_descriptions = {new: desc for _, new, desc in RENAMES}
    new_permission_ids: dict[str, str] = {}
    for code in NEW_CODES:
        permission_id = str(uuid.uuid4())
        new_permission_ids[code] = permission_id
        connection.execute(
            sa.text(
                """
                INSERT INTO permissions (id, code, module, description, created_at)
                VALUES (:id, :code, 'billing', :description, now())
                """
            ),
            {"id": permission_id, "code": code, "description": new_descriptions[code]},
        )

    # 2. Every role currently holding an old code is granted the matching
    #    new code (deduplicated - a role with both billing.view_services and
    #    billing.view_invoices only gets one billing.view grant).
    for old_code, new_code, _ in RENAMES:
        connection.execute(
            sa.text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT DISTINCT rp.role_id, CAST(:new_permission_id AS uuid)
                FROM role_permissions rp
                JOIN permissions p ON p.id = rp.permission_id
                WHERE p.code = :old_code
                AND NOT EXISTS (
                    SELECT 1 FROM role_permissions existing
                    WHERE existing.role_id = rp.role_id AND existing.permission_id = CAST(:new_permission_id AS uuid)
                )
                """
            ),
            {"old_code": old_code, "new_permission_id": new_permission_ids[new_code]},
        )

    # 3. Remove the old grants and permission rows.
    connection.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (SELECT id FROM permissions WHERE code = ANY(:codes))
            """
        ),
        {"codes": OLD_CODES},
    )
    connection.execute(sa.text("DELETE FROM permissions WHERE code = ANY(:codes)"), {"codes": OLD_CODES})


def downgrade() -> None:
    connection = op.get_bind()

    old_descriptions = {
        "billing.view_services": "View the service and package master catalog",
        "billing.view_invoices": "View invoices, payments, deposits, and receipts",
        "billing.create_invoice": "Create invoices and charges",
        "billing.collect_payment": "Collect payments and deposits",
        "billing.refund": "Refund payments and deposits",
    }
    old_permission_ids: dict[str, str] = {}
    for code in OLD_CODES:
        permission_id = str(uuid.uuid4())
        old_permission_ids[code] = permission_id
        connection.execute(
            sa.text(
                """
                INSERT INTO permissions (id, code, module, description, created_at)
                VALUES (:id, :code, 'billing', :description, now())
                """
            ),
            {"id": permission_id, "code": code, "description": old_descriptions[code]},
        )

    # billing.view fans back out to both billing.view_services and
    # billing.view_invoices for any role that held it.
    for old_code, new_code, _ in RENAMES:
        connection.execute(
            sa.text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT DISTINCT rp.role_id, CAST(:old_permission_id AS uuid)
                FROM role_permissions rp
                JOIN permissions p ON p.id = rp.permission_id
                WHERE p.code = :new_code
                AND NOT EXISTS (
                    SELECT 1 FROM role_permissions existing
                    WHERE existing.role_id = rp.role_id AND existing.permission_id = CAST(:old_permission_id AS uuid)
                )
                """
            ),
            {"new_code": new_code, "old_permission_id": old_permission_ids[old_code]},
        )

    connection.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (SELECT id FROM permissions WHERE code = ANY(:codes))
            """
        ),
        {"codes": NEW_CODES},
    )
    connection.execute(sa.text("DELETE FROM permissions WHERE code = ANY(:codes)"), {"codes": NEW_CODES})
