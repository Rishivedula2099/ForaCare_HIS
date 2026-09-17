"""link demo doctor to demo doctor user

Sets `doctors.user_id` on the demo "Dr. Priya Nair" (Cardiology) row to the
existing demo DOCTOR-role login (`dr.priya`), so the P3-F05/P3-B04
consultation flow's "assigned doctor" enforcement has a real account to
test end-to-end out of the box. Local/dev demo data only.

Revision ID: a6f1c94b3d82
Revises: d8e3a5c72f19
Create Date: 2026-09-17 10:02:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a6f1c94b3d82'
down_revision: Union[str, None] = 'd8e3a5c72f19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DOCTOR_ROW_ID = "66666666-6666-6666-6666-666666666602"
DOCTOR_USER_ID = "33333333-3333-3333-3333-333333333304"


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE doctors SET user_id = :user_id WHERE id = :id"),
        {"user_id": DOCTOR_USER_ID, "id": DOCTOR_ROW_ID},
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE doctors SET user_id = NULL WHERE id = :id"),
        {"id": DOCTOR_ROW_ID},
    )
