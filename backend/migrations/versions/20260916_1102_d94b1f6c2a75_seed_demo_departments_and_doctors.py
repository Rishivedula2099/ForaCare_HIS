"""seed demo departments and doctors

Seeds 5 demo departments and 6 demo doctors against the existing demo
tenant + main facility, so the OPD Department/Doctor master screens
(P3-F01) have real records to browse out of the box. Local/dev only.

Revision ID: d94b1f6c2a75
Revises: a7d59c2b4e83
Create Date: 2026-09-16 11:02:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd94b1f6c2a75'
down_revision: Union[str, None] = 'a7d59c2b4e83'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_ID = "11111111-1111-1111-1111-111111111111"
FACILITY_MAIN_ID = "22222222-2222-2222-2222-222222222201"

DEPARTMENTS = [
    dict(id="55555555-5555-5555-5555-555555555501", name="General Medicine", code="GENMED",
         description="Primary care and internal medicine consultations."),
    dict(id="55555555-5555-5555-5555-555555555502", name="Cardiology", code="CARDIO",
         description="Heart and cardiovascular care."),
    dict(id="55555555-5555-5555-5555-555555555503", name="Orthopedics", code="ORTHO",
         description="Bone, joint, and musculoskeletal care."),
    dict(id="55555555-5555-5555-5555-555555555504", name="Pediatrics", code="PEDS",
         description="Child and adolescent healthcare."),
    dict(id="55555555-5555-5555-5555-555555555505", name="Dermatology", code="DERMA",
         description="Skin, hair, and nail care."),
]

DOCTORS = [
    dict(id="66666666-6666-6666-6666-666666666601", department_id="55555555-5555-5555-5555-555555555501",
         doctor_code="DR-FC01-0001", full_name="Dr. Anil Sharma", specialization="Internal Medicine",
         qualification="MBBS, MD", phone="9811100001", email="anil.sharma@foracare-his.com",
         consultation_fee="500.00"),
    dict(id="66666666-6666-6666-6666-666666666602", department_id="55555555-5555-5555-5555-555555555502",
         doctor_code="DR-FC01-0002", full_name="Dr. Priya Nair", specialization="Interventional Cardiology",
         qualification="MBBS, DM Cardiology", phone="9811100002", email="priya.nair@foracare-his.com",
         consultation_fee="900.00"),
    dict(id="66666666-6666-6666-6666-666666666603", department_id="55555555-5555-5555-5555-555555555502",
         doctor_code="DR-FC01-0003", full_name="Dr. Vikram Rathore", specialization="Cardiac Electrophysiology",
         qualification="MBBS, MD, DM", phone="9811100003", email="vikram.rathore@foracare-his.com",
         consultation_fee="950.00"),
    dict(id="66666666-6666-6666-6666-666666666604", department_id="55555555-5555-5555-5555-555555555503",
         doctor_code="DR-FC01-0004", full_name="Dr. Meera Iyer", specialization="Joint Replacement Surgery",
         qualification="MBBS, MS Ortho", phone="9811100004", email="meera.iyer@foracare-his.com",
         consultation_fee="700.00"),
    dict(id="66666666-6666-6666-6666-666666666605", department_id="55555555-5555-5555-5555-555555555504",
         doctor_code="DR-FC01-0005", full_name="Dr. Karan Malhotra", specialization="Neonatology",
         qualification="MBBS, MD Pediatrics", phone="9811100005", email="karan.malhotra@foracare-his.com",
         consultation_fee="600.00"),
    dict(id="66666666-6666-6666-6666-666666666606", department_id="55555555-5555-5555-5555-555555555505",
         doctor_code="DR-FC01-0006", full_name="Dr. Ritu Desai", specialization="Cosmetic Dermatology",
         qualification="MBBS, MD Dermatology", phone="9811100006", email="ritu.desai@foracare-his.com",
         consultation_fee="650.00"),
]


def upgrade() -> None:
    connection = op.get_bind()

    for dept in DEPARTMENTS:
        connection.execute(
            sa.text(
                """
                INSERT INTO departments (id, tenant_id, facility_id, name, code, description, is_active, created_at, updated_at)
                VALUES (:id, :tenant_id, :facility_id, :name, :code, :description, true, now(), now())
                """
            ),
            {**dept, "tenant_id": TENANT_ID, "facility_id": FACILITY_MAIN_ID},
        )

    for doctor in DOCTORS:
        connection.execute(
            sa.text(
                """
                INSERT INTO doctors
                    (id, tenant_id, facility_id, department_id, doctor_code, full_name, specialization,
                     qualification, phone, email, consultation_fee, is_active, created_at, updated_at)
                VALUES
                    (:id, :tenant_id, :facility_id, :department_id, :doctor_code, :full_name, :specialization,
                     :qualification, :phone, :email, :consultation_fee, true, now(), now())
                """
            ),
            {**doctor, "tenant_id": TENANT_ID, "facility_id": FACILITY_MAIN_ID},
        )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text("DELETE FROM doctors WHERE id = ANY(:ids)"),
        {"ids": [d["id"] for d in DOCTORS]},
    )
    connection.execute(
        sa.text("DELETE FROM departments WHERE id = ANY(:ids)"),
        {"ids": [d["id"] for d in DEPARTMENTS]},
    )
