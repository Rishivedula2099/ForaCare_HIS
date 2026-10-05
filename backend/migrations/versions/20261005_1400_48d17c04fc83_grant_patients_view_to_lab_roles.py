"""grant patients.view to LAB_TECH and LAB_APPROVER

P6-F03 bug fix: accessioning (and anywhere else lab staff need to find a
patient by name/UID/MRN before folding their billed orders into an
accession) calls the patients search endpoint, which is gated on
`patients.view`. Neither `LAB_TECH` nor `LAB_APPROVER` held it, so that
lookup 403'd and the frontend's generic GET-403 handler bounced the user to
/forbidden - a read-only patient lookup should not have required the full
`patients.manage` authority these roles were never meant to have either.

Revision ID: 48d17c04fc83
Revises: 7062071914ec
Create Date: 2026-10-05 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '48d17c04fc83'
down_revision: Union[str, None] = '7062071914ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ROLE_CODES = ["LAB_TECH", "LAB_APPROVER"]


def upgrade() -> None:
    connection = op.get_bind()
    for role_code in ROLE_CODES:
        connection.execute(
            sa.text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT r.id, p.id FROM roles r, permissions p
                WHERE r.code = :role_code AND p.code = 'patients.view'
                ON CONFLICT DO NOTHING
                """
            ),
            {"role_code": role_code},
        )


def downgrade() -> None:
    connection = op.get_bind()
    for role_code in ROLE_CODES:
        connection.execute(
            sa.text(
                """
                DELETE FROM role_permissions
                WHERE role_id = (SELECT id FROM roles WHERE code = :role_code)
                  AND permission_id = (SELECT id FROM permissions WHERE code = 'patients.view')
                """
            ),
            {"role_code": role_code},
        )
