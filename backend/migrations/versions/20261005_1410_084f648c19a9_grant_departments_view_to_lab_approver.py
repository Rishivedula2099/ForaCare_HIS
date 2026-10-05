"""grant departments.view to LAB_APPROVER

P6-F01 bug fix: the Test master form (gated on `lab.manage_master`, which
`LAB_APPROVER` holds) has an optional department picker that fetches the
department list on open - gated on `departments.view`, which this role
never held. Same class of bug as the `patients.view` gap fixed in
48d17c04fc83: a read-only lookup a role's own screens depend on wasn't
actually granted, so opening "Add Test" 403'd and bounced the user to
/forbidden via the frontend's generic GET-403 handler.

Revision ID: 084f648c19a9
Revises: 48d17c04fc83
Create Date: 2026-10-05 14:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '084f648c19a9'
down_revision: Union[str, None] = '48d17c04fc83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id FROM roles r, permissions p
            WHERE r.code = 'LAB_APPROVER' AND p.code = 'departments.view'
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
            WHERE role_id = (SELECT id FROM roles WHERE code = 'LAB_APPROVER')
              AND permission_id = (SELECT id FROM permissions WHERE code = 'departments.view')
            """
        )
    )
