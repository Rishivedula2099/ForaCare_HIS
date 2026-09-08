"""seed second tenant for cross tenant isolation testing

Seeds a second, unrelated tenant (with its own facility and hospital admin
user) so tests can verify that a caller authenticated against one tenant
never sees another tenant's facilities, roles, or audit logs (see P1-B06
multi-tenancy). Demo password is "Demo@123", same as the primary pilot
tenant - local/dev only, never run this against a production database.

Revision ID: 58a45564ebbe
Revises: 70f2aaaf9ebb
Create Date: 2026-09-08 07:42:16.385542

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.security import hash_password

# revision identifiers, used by Alembic.
revision: str = '58a45564ebbe'
down_revision: Union[str, None] = '70f2aaaf9ebb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEMO_PASSWORD = "Demo@123"

TENANT_ID = "44444444-4444-4444-4444-444444444401"
FACILITY_ID = "44444444-4444-4444-4444-444444444402"
USER_ID = "44444444-4444-4444-4444-444444444403"


def upgrade() -> None:
    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            INSERT INTO tenants (id, name, slug, code, is_active, created_at)
            VALUES (:id, 'Sunrise Health Group', 'sunrise', 'SUNRISE', true, now())
            """
        ),
        {"id": TENANT_ID},
    )

    connection.execute(
        sa.text(
            """
            INSERT INTO facilities
                (id, tenant_id, name, facility_code, timezone, currency, is_active, created_at)
            VALUES
                (:id, :tenant_id, 'Sunrise General Hospital', 'SUN-MAIN-01', 'Asia/Kolkata', 'INR',
                 true, now())
            """
        ),
        {"id": FACILITY_ID, "tenant_id": TENANT_ID},
    )

    role_id = connection.execute(
        sa.text("SELECT id FROM roles WHERE code = 'HOSPITAL_ADMIN'")
    ).scalar_one()

    connection.execute(
        sa.text(
            """
            INSERT INTO users
                (id, tenant_id, facility_id, username, email, password_hash, full_name, role_id,
                 is_active, created_at, updated_at)
            VALUES
                (:id, :tenant_id, :facility_id, 'sunrise.admin', 'admin@sunrise-health.example',
                 :password_hash, 'Farah Osei', :role_id, true, now(), now())
            """
        ),
        {
            "id": USER_ID,
            "tenant_id": TENANT_ID,
            "facility_id": FACILITY_ID,
            "password_hash": hash_password(DEMO_PASSWORD),
            "role_id": role_id,
        },
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("DELETE FROM users WHERE tenant_id = :id"), {"id": TENANT_ID})
    connection.execute(sa.text("DELETE FROM facilities WHERE tenant_id = :id"), {"id": TENANT_ID})
    connection.execute(sa.text("DELETE FROM tenants WHERE id = :id"), {"id": TENANT_ID})
