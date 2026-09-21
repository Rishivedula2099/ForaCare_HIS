"""seed billing permissions

P5-B01: adds the `billing.view_services`, `billing.manage_services`,
`billing.view_invoices`, and `billing.refund` permission rows (the
`billing.create_invoice`/`billing.collect_payment` codes were already
seeded in 20260908_1005_..._seed_rbac_data_and_migrate_users.py) and grants
each role the codes listed for it in `ROLE_PERMISSION_SEED` - SUPER_ADMIN
via `ALL_PERMISSION_CODES`, HOSPITAL_ADMIN and BILLING_CASHIER get the new
billing codes directly.

Revision ID: d6f2a83c91be
Revises: b8e1d4f927ac
Create Date: 2026-09-21 10:01:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.modules.rbac.constants import PERMISSION_CATALOG, ROLE_PERMISSION_SEED

# revision identifiers, used by Alembic.
revision: str = 'd6f2a83c91be'
down_revision: Union[str, None] = 'b8e1d4f927ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PERMISSION_CODES = [
    "billing.view_services",
    "billing.manage_services",
    "billing.view_invoices",
    "billing.refund",
]


def upgrade() -> None:
    connection = op.get_bind()

    catalog_by_code = {code: (module, description) for code, module, description in PERMISSION_CATALOG}
    permission_ids = {code: str(uuid.uuid4()) for code in NEW_PERMISSION_CODES}

    for code in NEW_PERMISSION_CODES:
        module, description = catalog_by_code[code]
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

    for role_code, permission_codes in ROLE_PERMISSION_SEED.items():
        role_id = role_ids_by_code.get(role_code)
        if role_id is None:
            continue
        for permission_code in permission_codes:
            if permission_code not in permission_ids:
                continue
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
