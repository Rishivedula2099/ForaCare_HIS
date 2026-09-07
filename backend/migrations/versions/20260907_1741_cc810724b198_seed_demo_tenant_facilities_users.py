"""seed demo tenant, facilities, users

Seeds one pilot tenant, three facilities, and one demo user per role so the
login flow is testable end-to-end without a separate admin UI (see
ASM-OPS-01: pilot hospital as a single initial tenant). All demo users share
the password "Demo@123" - local/dev environments only, never run this
against a production database.

Revision ID: cc810724b198
Revises: ac0f87b76328
Create Date: 2026-09-07 17:41:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.core.security import hash_password

# revision identifiers, used by Alembic.
revision: str = 'cc810724b198'
down_revision: Union[str, None] = 'ac0f87b76328'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEMO_PASSWORD = "Demo@123"

TENANT_ID = "11111111-1111-1111-1111-111111111111"

FACILITY_MAIN_ID = "22222222-2222-2222-2222-222222222201"
FACILITY_SOUTH_ID = "22222222-2222-2222-2222-222222222202"
FACILITY_METRO_ID = "22222222-2222-2222-2222-222222222203"

DEMO_USERS = [
    dict(
        id="33333333-3333-3333-3333-333333333301",
        facility_id=FACILITY_MAIN_ID,
        username="super.admin",
        email="super.admin@foracare-his.com",
        full_name="Ananya Kapoor",
        role="SUPER_ADMIN",
    ),
    dict(
        id="33333333-3333-3333-3333-333333333302",
        facility_id=FACILITY_MAIN_ID,
        username="hospital.admin",
        email="hospital.admin@foracare-his.com",
        full_name="Vikram Seth",
        role="HOSPITAL_ADMIN",
    ),
    dict(
        id="33333333-3333-3333-3333-333333333303",
        facility_id=FACILITY_MAIN_ID,
        username="receptionist",
        email="rahul.deshmukh@foracare-his.com",
        full_name="Rahul Deshmukh",
        role="RECEPTIONIST",
    ),
    dict(
        id="33333333-3333-3333-3333-333333333304",
        facility_id=FACILITY_MAIN_ID,
        username="dr.priya",
        email="priya.raman@foracare-his.com",
        full_name="Dr. Priya Raman",
        role="DOCTOR",
    ),
    dict(
        id="33333333-3333-3333-3333-333333333305",
        facility_id=FACILITY_MAIN_ID,
        username="nurse.mary",
        email="mary.joseph@foracare-his.com",
        full_name="Sister Mary Joseph",
        role="NURSE",
    ),
    dict(
        id="33333333-3333-3333-3333-333333333306",
        facility_id=FACILITY_METRO_ID,
        username="lab.tech",
        email="lab.tech@foracare-his.com",
        full_name="Sanjay Iyer",
        role="LAB_TECH",
    ),
    dict(
        id="33333333-3333-3333-3333-333333333307",
        facility_id=FACILITY_METRO_ID,
        username="lab.approver",
        email="anirudh.sen@foracare-his.com",
        full_name="Dr. Anirudh Sen",
        role="LAB_APPROVER",
    ),
    dict(
        id="33333333-3333-3333-3333-333333333308",
        facility_id=FACILITY_SOUTH_ID,
        username="auditor",
        email="auditor@foracare-his.com",
        full_name="Meera Nair",
        role="AUDITOR",
    ),
]


def upgrade() -> None:
    connection = op.get_bind()

    connection.execute(
        sa.text(
            """
            INSERT INTO tenants (id, name, slug, code, is_active, created_at)
            VALUES (:id, :name, :slug, :code, true, now())
            """
        ),
        {
            "id": TENANT_ID,
            "name": "ForaCare Health Network",
            "slug": "foracare",
            "code": "FORACARE",
        },
    )

    facilities = [
        dict(
            id=FACILITY_MAIN_ID,
            name="ForaCare City Hospital (Main Branch)",
            facility_code="FC-MAIN-01",
        ),
        dict(
            id=FACILITY_SOUTH_ID,
            name="ForaCare South Clinic",
            facility_code="FC-ST-02",
        ),
        dict(
            id=FACILITY_METRO_ID,
            name="ForaCare Metro Diagnostic Center",
            facility_code="FC-METRO-03",
        ),
    ]
    for facility in facilities:
        connection.execute(
            sa.text(
                """
                INSERT INTO facilities
                    (id, tenant_id, name, facility_code, timezone, currency, is_active, created_at)
                VALUES
                    (:id, :tenant_id, :name, :facility_code, 'Asia/Kolkata', 'INR', true, now())
                """
            ),
            {"tenant_id": TENANT_ID, **facility},
        )

    password_hash = hash_password(DEMO_PASSWORD)
    for user in DEMO_USERS:
        connection.execute(
            sa.text(
                """
                INSERT INTO users
                    (id, tenant_id, facility_id, username, email, password_hash, full_name, role,
                     is_active, created_at, updated_at)
                VALUES
                    (:id, :tenant_id, :facility_id, :username, :email, :password_hash, :full_name,
                     :role, true, now(), now())
                """
            ),
            {"tenant_id": TENANT_ID, "password_hash": password_hash, **user},
        )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("DELETE FROM users WHERE tenant_id = :tenant_id"), {"tenant_id": TENANT_ID})
    connection.execute(
        sa.text("DELETE FROM facilities WHERE tenant_id = :tenant_id"), {"tenant_id": TENANT_ID}
    )
    connection.execute(sa.text("DELETE FROM tenants WHERE id = :id"), {"id": TENANT_ID})
