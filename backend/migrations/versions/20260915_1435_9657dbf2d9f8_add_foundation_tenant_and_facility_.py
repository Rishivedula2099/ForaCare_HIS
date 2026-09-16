"""add foundation tenant and facility indexes

Every tenant-scoped query (see app/shared/tenancy.py scope_to_tenant) filters
on tenant_id and facility_id, but patients/users/facilities had no index
covering those columns - only their unique business identifiers (uid, mrn,
username, email, facility_code) were indexed. Adds composite indexes to
back the multi-tenancy isolation boundary and facility-scoped listing
queries used across the app.

Revision ID: 9657dbf2d9f8
Revises: c340fcb4ffa0
Create Date: 2026-09-15 14:35:11.993859

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9657dbf2d9f8'
down_revision: Union[str, None] = 'c340fcb4ffa0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        op.f("ix_patients_tenant_id_facility_id"), "patients", ["tenant_id", "facility_id"]
    )
    op.create_index(
        op.f("ix_users_tenant_id_facility_id"), "users", ["tenant_id", "facility_id"]
    )
    op.create_index(op.f("ix_facilities_tenant_id"), "facilities", ["tenant_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_facilities_tenant_id"), table_name="facilities")
    op.drop_index(op.f("ix_users_tenant_id_facility_id"), table_name="users")
    op.drop_index(op.f("ix_patients_tenant_id_facility_id"), table_name="patients")
