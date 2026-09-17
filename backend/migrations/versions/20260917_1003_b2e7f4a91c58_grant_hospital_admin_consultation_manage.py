"""grant hospital admin consultations.manage

The consultation "assigned doctor or admin override" rule
(`_ensure_can_manage_consultation` in app/modules/opd/service.py) only
matters if HOSPITAL_ADMIN can reach it at all - the prior seed migration
(d8e3a5c72f19) granted HOSPITAL_ADMIN `consultations.view` but not
`consultations.manage`, making the override dead code. Grants the missing
permission rather than editing the already-applied seed migration.

Revision ID: b2e7f4a91c58
Revises: a6f1c94b3d82
Create Date: 2026-09-17 10:03:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2e7f4a91c58'
down_revision: Union[str, None] = 'a6f1c94b3d82'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r, permissions p
            WHERE r.code = 'HOSPITAL_ADMIN' AND p.code = 'consultations.manage'
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE role_id = (SELECT id FROM roles WHERE code = 'HOSPITAL_ADMIN')
              AND permission_id = (SELECT id FROM permissions WHERE code = 'consultations.manage')
            """
        )
    )
