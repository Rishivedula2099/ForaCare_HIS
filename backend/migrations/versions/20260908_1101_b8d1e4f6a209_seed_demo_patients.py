"""seed demo patients

Seeds 5 demo patients (with address/contact/identifier/ABHA link rows)
against the existing demo tenant + main facility, mirroring the local
frontend mock data (`frontend/src/lib/patient-store.ts`) so Patient 360 has
real records to open out of the box. Local/dev only.

Revision ID: b8d1e4f6a209
Revises: a3f7c9e2b104
Create Date: 2026-09-08 11:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b8d1e4f6a209'
down_revision: Union[str, None] = 'a3f7c9e2b104'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TENANT_ID = "11111111-1111-1111-1111-111111111111"
FACILITY_MAIN_ID = "22222222-2222-2222-2222-222222222201"
RECEPTIONIST_ID = "33333333-3333-3333-3333-333333333303"

PATIENTS = [
    dict(
        id="44444444-4444-4444-4444-444444444401",
        uid="FC-MAIN-01-202609-000001",
        mrn="MRN-2026-000001",
        title="Mrs.",
        first_name="Sunita",
        last_name="Verma",
        gender="FEMALE",
        dob="1982-04-15",
        blood_group="B_POSITIVE",
        marital_status="MARRIED",
        occupation="School Teacher",
        preferred_language="Hindi",
        is_minor=False,
        address=dict(
            street="Flat 402, Green Valley Apartments, MG Road",
            city="Bengaluru",
            state="Karnataka",
            pincode="560001",
        ),
        contacts=[("MOBILE", "9876543210", True), ("EMAIL", "sunita.verma@example.com", False)],
        identifiers=[("AADHAAR", "567812349012", True)],
        abha=("91-4521-8890-1204", "sunita.verma@abdm", "VERIFIED"),
    ),
    dict(
        id="44444444-4444-4444-4444-444444444402",
        uid="FC-MAIN-01-202609-000002",
        mrn="MRN-2026-000002",
        title="Mr.",
        first_name="Rajesh",
        last_name="Kumar",
        gender="MALE",
        dob="1978-11-20",
        blood_group="O_POSITIVE",
        marital_status="MARRIED",
        occupation="Business Executive",
        preferred_language="English",
        is_minor=False,
        address=dict(
            street="House No 84, Indiranagar 2nd Stage",
            city="Bengaluru",
            state="Karnataka",
            pincode="560038",
        ),
        contacts=[("MOBILE", "9812345678", True), ("EMAIL", "rajesh.kumar78@example.com", False)],
        identifiers=[("PAN_CARD", "ABCDE1234F", True)],
        abha=("91-3344-5566-7788", "rajesh.kumar@sbx", "LINKED"),
    ),
    dict(
        id="44444444-4444-4444-4444-444444444403",
        uid="FC-MAIN-01-202609-000003",
        mrn="MRN-2026-000003",
        title="Ms.",
        first_name="Ananya",
        last_name="Sharma",
        gender="FEMALE",
        dob="1997-03-08",
        blood_group="A_POSITIVE",
        marital_status="SINGLE",
        occupation="Software Engineer",
        preferred_language="English",
        is_minor=False,
        address=dict(
            street="Flat 12B, Prestige Cyber Towers, Whitefield",
            city="Bengaluru",
            state="Karnataka",
            pincode="560066",
        ),
        contacts=[("MOBILE", "9945678901", True), ("EMAIL", "ananya.sharma@techcorp.io", False)],
        identifiers=[("PASSPORT", "Z8942105", True)],
        abha=("91-1122-3344-5566", "ananya.sharma@abdm", "VERIFIED"),
    ),
    dict(
        id="44444444-4444-4444-4444-444444444404",
        uid="FC-MAIN-01-202609-000004",
        mrn="MRN-2026-000004",
        title="Master",
        first_name="Aarav",
        last_name="Patel",
        gender="MALE",
        dob="2019-07-22",
        blood_group="O_POSITIVE",
        marital_status="SINGLE",
        occupation=None,
        preferred_language="Gujarati",
        is_minor=True,
        guardian_name="Vikram Patel",
        guardian_relationship="FATHER",
        guardian_phone="9723456780",
        guardian_address="B-14, Shanti Niketan Society, Outer Ring Road, Bengaluru",
        address=dict(
            street="B-14, Shanti Niketan Society, Outer Ring Road",
            city="Bengaluru",
            state="Karnataka",
            pincode="560103",
        ),
        contacts=[("MOBILE", "9723456780", True)],
        identifiers=[("AADHAAR", "458923019944", False)],
        abha=None,
    ),
    dict(
        id="44444444-4444-4444-4444-444444444405",
        uid="FC-MAIN-01-202609-000005",
        mrn="MRN-2026-000005",
        title="Mr.",
        first_name="Mohammed",
        middle_name="Irfan",
        last_name="Khan",
        gender="MALE",
        dob="1965-10-10",
        blood_group="AB_POSITIVE",
        marital_status="MARRIED",
        occupation="Retired Civil Officer",
        preferred_language="Urdu",
        is_minor=False,
        guardian_name="Farhan Khan",
        guardian_relationship="SON",
        guardian_phone="9448123999",
        address=dict(
            street="No. 29, Crescent Road, High Grounds",
            city="Bengaluru",
            state="Karnataka",
            pincode="560001",
        ),
        contacts=[("MOBILE", "9448123987", True), ("EMAIL", "irfan.khan@example.org", False)],
        identifiers=[("VOTER_ID", "KAR0981245", True)],
        abha=("91-7788-9900-1122", "irfan.khan@abdm", "VERIFIED"),
    ),
]


def upgrade() -> None:
    connection = op.get_bind()

    for patient in PATIENTS:
        connection.execute(
            sa.text(
                """
                INSERT INTO patients
                    (id, tenant_id, facility_id, uid, mrn, title, first_name, middle_name, last_name,
                     gender, dob, blood_group, marital_status, occupation, preferred_language, is_minor,
                     guardian_name, guardian_relationship, guardian_phone, guardian_address, status,
                     registered_by, created_at, updated_at)
                VALUES
                    (:id, :tenant_id, :facility_id, :uid, :mrn, :title, :first_name, :middle_name, :last_name,
                     :gender, :dob, :blood_group, :marital_status, :occupation, :preferred_language, :is_minor,
                     :guardian_name, :guardian_relationship, :guardian_phone, :guardian_address, 'ACTIVE',
                     :registered_by, now(), now())
                """
            ),
            {
                "tenant_id": TENANT_ID,
                "facility_id": FACILITY_MAIN_ID,
                "registered_by": RECEPTIONIST_ID,
                "middle_name": patient.get("middle_name"),
                "guardian_name": patient.get("guardian_name"),
                "guardian_relationship": patient.get("guardian_relationship"),
                "guardian_phone": patient.get("guardian_phone"),
                "guardian_address": patient.get("guardian_address"),
                **{
                    k: v
                    for k, v in patient.items()
                    if k not in ("address", "contacts", "identifiers", "abha", "middle_name",
                                 "guardian_name", "guardian_relationship", "guardian_phone", "guardian_address")
                },
            },
        )

        address = patient["address"]
        connection.execute(
            sa.text(
                """
                INSERT INTO patient_addresses (id, patient_id, address_type, street, city, state, pincode, country)
                VALUES (gen_random_uuid(), :patient_id, 'PERMANENT', :street, :city, :state, :pincode, 'India')
                """
            ),
            {"patient_id": patient["id"], **address},
        )

        for contact_type, value, is_primary in patient["contacts"]:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO patient_contacts (id, patient_id, contact_type, value, is_primary)
                    VALUES (gen_random_uuid(), :patient_id, :contact_type, :value, :is_primary)
                    """
                ),
                {
                    "patient_id": patient["id"],
                    "contact_type": contact_type,
                    "value": value,
                    "is_primary": is_primary,
                },
            )

        for identity_type, id_number, is_verified in patient["identifiers"]:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO patient_identifiers
                        (id, patient_id, identity_type, id_number, is_verified, verified_at)
                    VALUES
                        (gen_random_uuid(), :patient_id, :identity_type, :id_number, :is_verified,
                         CASE WHEN :is_verified THEN now() ELSE NULL END)
                    """
                ),
                {
                    "patient_id": patient["id"],
                    "identity_type": identity_type,
                    "id_number": id_number,
                    "is_verified": is_verified,
                },
            )

        if patient["abha"]:
            external_id, external_address, status = patient["abha"]
            connection.execute(
                sa.text(
                    """
                    INSERT INTO patient_identity_links
                        (id, patient_id, system, external_id, external_address, status, linked_at)
                    VALUES
                        (gen_random_uuid(), :patient_id, 'ABHA', :external_id, :external_address, :status, now())
                    """
                ),
                {
                    "patient_id": patient["id"],
                    "external_id": external_id,
                    "external_address": external_address,
                    "status": status,
                },
            )
        else:
            connection.execute(
                sa.text(
                    """
                    INSERT INTO patient_identity_links (id, patient_id, system, status)
                    VALUES (gen_random_uuid(), :patient_id, 'ABHA', 'UNVERIFIED')
                    """
                ),
                {"patient_id": patient["id"]},
            )


def downgrade() -> None:
    connection = op.get_bind()
    patient_ids = tuple(patient["id"] for patient in PATIENTS)
    connection.execute(
        sa.text("DELETE FROM patient_identity_links WHERE patient_id = ANY(:ids)"), {"ids": list(patient_ids)}
    )
    connection.execute(
        sa.text("DELETE FROM patient_identifiers WHERE patient_id = ANY(:ids)"), {"ids": list(patient_ids)}
    )
    connection.execute(
        sa.text("DELETE FROM patient_contacts WHERE patient_id = ANY(:ids)"), {"ids": list(patient_ids)}
    )
    connection.execute(
        sa.text("DELETE FROM patient_addresses WHERE patient_id = ANY(:ids)"), {"ids": list(patient_ids)}
    )
    connection.execute(sa.text("DELETE FROM patients WHERE id = ANY(:ids)"), {"ids": list(patient_ids)})
