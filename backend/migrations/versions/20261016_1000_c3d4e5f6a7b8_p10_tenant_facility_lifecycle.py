"""P10-B02: tenant / facility lifecycle audit columns

Records why and by whom a tenant or facility was last suspended, deactivated or
reactivated. `is_active` stays the single switch every query already honours.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("tenants", "facilities"):
        op.add_column(table, sa.Column("status_reason", sa.Text(), nullable=True))
        op.add_column(table, sa.Column("status_changed_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column(table, sa.Column("status_changed_by", postgresql.UUID(as_uuid=True), nullable=True))
        op.create_foreign_key(
            f"fk_{table}_status_changed_by_users", table, "users", ["status_changed_by"], ["id"]
        )


def downgrade() -> None:
    for table in ("facilities", "tenants"):
        op.drop_constraint(f"fk_{table}_status_changed_by_users", table, type_="foreignkey")
        op.drop_column(table, "status_changed_by")
        op.drop_column(table, "status_changed_at")
        op.drop_column(table, "status_reason")
