"""grant documents.print to HOSPITAL_ADMIN

P7-B06: every generated document now requires `documents.print` in addition
to the module permission for its content. HOSPITAL_ADMIN held the module
permissions (and `documents.manage_templates`) but never `documents.print`,
so without this grant it would lose the ability to produce the documents it
could previously open.

Revision ID: d4a2f6b8c901
Revises: c3e91a5d7b42
Create Date: 2026-10-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd4a2f6b8c901'
down_revision: Union[str, None] = 'c3e91a5d7b42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.get_bind().execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id FROM roles r, permissions p
            WHERE r.code = 'HOSPITAL_ADMIN' AND p.code = 'documents.print'
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.get_bind().execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE role_id IN (SELECT id FROM roles WHERE code = 'HOSPITAL_ADMIN')
              AND permission_id IN (SELECT id FROM permissions WHERE code = 'documents.print')
            """
        )
    )
