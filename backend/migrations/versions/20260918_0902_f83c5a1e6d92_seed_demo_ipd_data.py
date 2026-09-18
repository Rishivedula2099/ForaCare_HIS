"""seed demo ipd wards, rooms, and beds

Seeds 3 demo wards (General, ICU, Private), a couple of rooms per ward, and
beds in each room against the existing demo tenant + main facility, so the
Ward/Room/Bed board screens (P4-F01) have real records to browse out of the
box. Local/dev only - mirrors d94b1f6c2a75's approach for departments/doctors.

Revision ID: f83c5a1e6d92
Revises: d29a6f731b84
Create Date: 2026-09-18 09:02:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f83c5a1e6d92'
down_revision: Union[str, None] = 'd29a6f731b84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_ID = "11111111-1111-1111-1111-111111111111"
FACILITY_MAIN_ID = "22222222-2222-2222-2222-222222222201"
DEPT_GENMED_ID = "55555555-5555-5555-5555-555555555501"

WARDS = [
    dict(id="77777777-7777-7777-7777-777777777701", department_id=DEPT_GENMED_ID,
         name="General Ward A", code="GW-A", ward_type="GENERAL", floor="1"),
    dict(id="77777777-7777-7777-7777-777777777702", department_id=None,
         name="ICU", code="ICU-1", ward_type="ICU", floor="2"),
    dict(id="77777777-7777-7777-7777-777777777703", department_id=None,
         name="Private Ward", code="PVT-1", ward_type="PRIVATE", floor="3"),
]

ROOMS = [
    dict(id="88888888-8888-8888-8888-888888888801", ward_id="77777777-7777-7777-7777-777777777701",
         room_number="101", room_type="GENERAL"),
    dict(id="88888888-8888-8888-8888-888888888802", ward_id="77777777-7777-7777-7777-777777777701",
         room_number="102", room_type="GENERAL"),
    dict(id="88888888-8888-8888-8888-888888888803", ward_id="77777777-7777-7777-7777-777777777702",
         room_number="ICU-201", room_type="ICU"),
    dict(id="88888888-8888-8888-8888-888888888804", ward_id="77777777-7777-7777-7777-777777777703",
         room_number="301", room_type="PRIVATE"),
]

BEDS = [
    dict(id="99999999-9999-9999-9999-999999999901", ward_id="77777777-7777-7777-7777-777777777701",
         room_id="88888888-8888-8888-8888-888888888801", bed_number="101-A"),
    dict(id="99999999-9999-9999-9999-999999999902", ward_id="77777777-7777-7777-7777-777777777701",
         room_id="88888888-8888-8888-8888-888888888801", bed_number="101-B"),
    dict(id="99999999-9999-9999-9999-999999999903", ward_id="77777777-7777-7777-7777-777777777701",
         room_id="88888888-8888-8888-8888-888888888802", bed_number="102-A"),
    dict(id="99999999-9999-9999-9999-999999999904", ward_id="77777777-7777-7777-7777-777777777701",
         room_id="88888888-8888-8888-8888-888888888802", bed_number="102-B"),
    dict(id="99999999-9999-9999-9999-999999999905", ward_id="77777777-7777-7777-7777-777777777702",
         room_id="88888888-8888-8888-8888-888888888803", bed_number="ICU-201-1"),
    dict(id="99999999-9999-9999-9999-999999999906", ward_id="77777777-7777-7777-7777-777777777702",
         room_id="88888888-8888-8888-8888-888888888803", bed_number="ICU-201-2"),
    dict(id="99999999-9999-9999-9999-999999999907", ward_id="77777777-7777-7777-7777-777777777703",
         room_id="88888888-8888-8888-8888-888888888804", bed_number="301-A"),
]


def upgrade() -> None:
    connection = op.get_bind()

    for ward in WARDS:
        connection.execute(
            sa.text(
                """
                INSERT INTO ipd_wards
                    (id, tenant_id, facility_id, department_id, name, code, ward_type, floor, is_active, created_at, updated_at)
                VALUES
                    (:id, :tenant_id, :facility_id, :department_id, :name, :code, :ward_type, :floor, true, now(), now())
                """
            ),
            {**ward, "tenant_id": TENANT_ID, "facility_id": FACILITY_MAIN_ID},
        )

    for room in ROOMS:
        connection.execute(
            sa.text(
                """
                INSERT INTO ipd_rooms
                    (id, tenant_id, facility_id, ward_id, room_number, room_type, is_active, created_at, updated_at)
                VALUES
                    (:id, :tenant_id, :facility_id, :ward_id, :room_number, :room_type, true, now(), now())
                """
            ),
            {**room, "tenant_id": TENANT_ID, "facility_id": FACILITY_MAIN_ID},
        )

    for bed in BEDS:
        connection.execute(
            sa.text(
                """
                INSERT INTO ipd_beds
                    (id, tenant_id, facility_id, ward_id, room_id, bed_number, status, is_active, created_at, updated_at)
                VALUES
                    (:id, :tenant_id, :facility_id, :ward_id, :room_id, :bed_number, 'AVAILABLE', true, now(), now())
                """
            ),
            {**bed, "tenant_id": TENANT_ID, "facility_id": FACILITY_MAIN_ID},
        )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text("DELETE FROM ipd_beds WHERE id = ANY(:ids)"), {"ids": [b["id"] for b in BEDS]})
    connection.execute(sa.text("DELETE FROM ipd_rooms WHERE id = ANY(:ids)"), {"ids": [r["id"] for r in ROOMS]})
    connection.execute(sa.text("DELETE FROM ipd_wards WHERE id = ANY(:ids)"), {"ids": [w["id"] for w in WARDS]})
