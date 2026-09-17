"""seed opd.view permission

Adds the `opd.view` permission row (P3-B01/P3-F02 - read access to
encounters/tokens/queue, distinct from `opd.manage_queue` which already
existed and covers registering visits) and grants it to every role listed
for it in `ROLE_PERMISSION_SEED`.

Revision ID: e6a4d2c8f150
Revises: c2e7b91f0a34
Create Date: 2026-09-16 12:01:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.modules.rbac.constants import PERMISSION_CATALOG, ROLE_PERMISSION_SEED

# revision identifiers, used by Alembic.
revision: str = 'e6a4d2c8f150'
down_revision: Union[str, None] = 'c2e7b91f0a34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PERMISSION_CODES = ["opd.view"]


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
