"""seed rbac roles/permissions, migrate users onto role_id

Seeds the 9 system roles (adding BILLING_CASHIER, split out from
RECEPTIONIST per the RBAC role review) and a starting permission catalog,
maps role_permissions, backfills `users.role_id` from the legacy `role`
enum column, then drops that column and its enum type. Also seeds one new
demo user for BILLING_CASHIER (password "Demo@123", local/dev only - see
the seed migration this one follows).

Revision ID: e7c1f4a2b856
Revises: d4b2e6a91f03
Create Date: 2026-09-08 10:05:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.security import hash_password
from app.modules.rbac.constants import PERMISSION_CATALOG, ROLE_PERMISSION_SEED, SYSTEM_ROLE_NAMES

# revision identifiers, used by Alembic.
revision: str = 'e7c1f4a2b856'
down_revision: Union[str, None] = 'd4b2e6a91f03'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEMO_PASSWORD = "Demo@123"
TENANT_ID = "11111111-1111-1111-1111-111111111111"
FACILITY_MAIN_ID = "22222222-2222-2222-2222-222222222201"
BILLING_CASHIER_USER_ID = "33333333-3333-3333-3333-333333333309"


def upgrade() -> None:
    connection = op.get_bind()

    # Allow the new BILLING_CASHIER demo user to be inserted below without a
    # value in the legacy `role` enum column (it has no matching enum value).
    # The column is dropped entirely at the end of this migration anyway.
    op.alter_column('users', 'role', nullable=True)

    role_ids = {code: str(uuid.uuid4()) for code in SYSTEM_ROLE_NAMES}
    for code, role_id in role_ids.items():
        connection.execute(
            sa.text(
                """
                INSERT INTO roles (id, code, name, description, is_system, created_at, updated_at)
                VALUES (:id, :code, :name, :description, true, now(), now())
                """
            ),
            {
                "id": role_id,
                "code": code,
                "name": SYSTEM_ROLE_NAMES[code],
                "description": f"System role: {SYSTEM_ROLE_NAMES[code]}",
            },
        )

    permission_ids = {code: str(uuid.uuid4()) for code, _, _ in PERMISSION_CATALOG}
    for code, module, description in PERMISSION_CATALOG:
        connection.execute(
            sa.text(
                """
                INSERT INTO permissions (id, code, module, description, created_at)
                VALUES (:id, :code, :module, :description, now())
                """
            ),
            {"id": permission_ids[code], "code": code, "module": module, "description": description},
        )

    for role_code, permission_codes in ROLE_PERMISSION_SEED.items():
        for permission_code in permission_codes:
            connection.execute(
                sa.text(
                    "INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :permission_id)"
                ),
                {"role_id": role_ids[role_code], "permission_id": permission_ids[permission_code]},
            )

    connection.execute(
        sa.text(
            """
            INSERT INTO users
                (id, tenant_id, facility_id, username, email, password_hash, full_name, role_id,
                 is_active, created_at, updated_at)
            VALUES
                (:id, :tenant_id, :facility_id, :username, :email, :password_hash, :full_name, :role_id,
                 true, now(), now())
            """
        ),
        {
            "id": BILLING_CASHIER_USER_ID,
            "tenant_id": TENANT_ID,
            "facility_id": FACILITY_MAIN_ID,
            "username": "billing.cashier",
            "email": "billing.cashier@foracare-his.com",
            "password_hash": hash_password(DEMO_PASSWORD),
            "full_name": "Kavita Menon",
            "role_id": role_ids["BILLING_CASHIER"],
        },
    )

    connection.execute(
        sa.text(
            """
            UPDATE users u
            SET role_id = r.id
            FROM roles r
            WHERE r.code = u.role::text AND u.role_id IS NULL
            """
        )
    )

    op.alter_column('users', 'role_id', nullable=False)
    op.drop_column('users', 'role')
    op.execute(sa.text("DROP TYPE IF EXISTS user_role"))


def downgrade() -> None:
    connection = op.get_bind()

    user_role_enum = sa.Enum(
        'SUPER_ADMIN', 'HOSPITAL_ADMIN', 'RECEPTIONIST', 'DOCTOR', 'NURSE',
        'LAB_TECH', 'LAB_APPROVER', 'AUDITOR', name='user_role',
    )
    user_role_enum.create(connection, checkfirst=True)
    op.add_column('users', sa.Column('role', user_role_enum, nullable=True))
    connection.execute(
        sa.text(
            """
            UPDATE users u
            SET role = r.code::user_role
            FROM roles r
            WHERE r.id = u.role_id AND r.code != 'BILLING_CASHIER'
            """
        )
    )
    # BILLING_CASHIER didn't exist pre-migration; fold it back into RECEPTIONIST.
    connection.execute(sa.text("UPDATE users SET role = 'RECEPTIONIST' WHERE role IS NULL"))
    op.alter_column('users', 'role', nullable=False)

    connection.execute(sa.text("DELETE FROM users WHERE id = :id"), {"id": BILLING_CASHIER_USER_ID})
    op.alter_column('users', 'role_id', nullable=True)
    connection.execute(sa.text("UPDATE users SET role_id = NULL"))
    connection.execute(sa.text("DELETE FROM role_permissions"))
    connection.execute(sa.text("DELETE FROM permissions"))
    connection.execute(sa.text("DELETE FROM roles"))
