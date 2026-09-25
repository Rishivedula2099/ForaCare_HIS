"""seed lab.view and lab.manage_master permissions

P6-F01: adds the `lab.view` (module-level access, mirroring `billing.view`)
and `lab.manage_master` (Test/Parameter/ReferenceRange master CRUD)
permission rows and grants them per the current `ROLE_PERMISSION_SEED` in
app/modules/rbac/constants.py - these codes were added to that module
alongside the Lab Master service/API/schema layer, but never seeded into
the database.

`lab.view`: SUPER_ADMIN, HOSPITAL_ADMIN, DOCTOR, NURSE, RECEPTIONIST,
LAB_TECH, LAB_APPROVER, AUDITOR (every role except BILLING_CASHIER, which
holds no lab permissions at all).
`lab.manage_master`: SUPER_ADMIN, HOSPITAL_ADMIN, LAB_APPROVER.

Revision ID: f28d6c4a91be
Revises: e4a71c9b3f28
Create Date: 2026-09-25 09:01:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f28d6c4a91be'
down_revision: Union[str, None] = 'e4a71c9b3f28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PERMISSIONS = [
    ("lab.view", "lab", "View the laboratory module - test master, orders, and results"),
    ("lab.manage_master", "lab", "Create and update the lab test/parameter/reference-range master"),
]
NEW_PERMISSION_CODES = [code for code, _, _ in NEW_PERMISSIONS]

ROLE_GRANTS = {
    "SUPER_ADMIN": ["lab.view", "lab.manage_master"],
    "HOSPITAL_ADMIN": ["lab.view", "lab.manage_master"],
    "DOCTOR": ["lab.view"],
    "NURSE": ["lab.view"],
    "RECEPTIONIST": ["lab.view"],
    "LAB_TECH": ["lab.view"],
    "LAB_APPROVER": ["lab.view", "lab.manage_master"],
    "AUDITOR": ["lab.view"],
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
    connection.execute(sa.text("DELETE FROM permissions WHERE code = ANY(:codes)"), {"codes": NEW_PERMISSION_CODES})
