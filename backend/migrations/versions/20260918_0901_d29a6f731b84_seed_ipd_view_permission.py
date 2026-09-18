"""seed ipd.view permission and backfill ipd.manage_beds grants

Adds the `ipd.view` permission row (P4-B01/P4-F01 - read access to wards,
rooms, beds, and admissions, distinct from `ipd.manage_beds` which already
existed) and grants both codes per `ROLE_PERMISSION_SEED` -
`ipd.manage_beds` was previously only granted to DOCTOR/NURSE; this also
backfills the HOSPITAL_ADMIN grant now that ward/room/bed master-data setup
needs it too (mirrors b2e7f4a91c58's "grant missing permission" approach).

Revision ID: d29a6f731b84
Revises: c1d4e8a53f67
Create Date: 2026-09-18 09:01:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.modules.rbac.constants import PERMISSION_CATALOG, ROLE_PERMISSION_SEED

# revision identifiers, used by Alembic.
revision: str = 'd29a6f731b84'
down_revision: Union[str, None] = 'c1d4e8a53f67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

NEW_PERMISSION_CODES = ["ipd.view"]
BACKFILL_GRANT_CODES = ["ipd.view", "ipd.manage_beds"]


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
            if permission_code not in BACKFILL_GRANT_CODES:
                continue
            connection.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT :role_id, p.id FROM permissions p WHERE p.code = :permission_code
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"role_id": role_id, "permission_code": permission_code},
            )


def downgrade() -> None:
    connection = op.get_bind()
    # Undo the HOSPITAL_ADMIN backfill grant this migration added for the
    # pre-existing `ipd.manage_beds` code (DOCTOR/NURSE already had it before
    # this migration and are left untouched).
    connection.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE role_id = (SELECT id FROM roles WHERE code = 'HOSPITAL_ADMIN')
              AND permission_id = (SELECT id FROM permissions WHERE code = 'ipd.manage_beds')
            """
        )
    )
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
