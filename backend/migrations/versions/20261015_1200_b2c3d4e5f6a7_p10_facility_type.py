"""P10-F02: facility type (hospital / clinic / medical centre)

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "facilities",
        sa.Column("facility_type", sa.String(length=30), nullable=False, server_default="hospital"),
    )
    op.create_check_constraint(
        "ck_facilities_facility_type",
        "facilities",
        "facility_type IN ('hospital', 'clinic', 'medical_centre')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_facilities_facility_type", "facilities", type_="check")
    op.drop_column("facilities", "facility_type")
