"""abha link permissions and identity-link uniqueness

P8-B05: adds the `patients.link_abha` and `patients.unlink_abha` permissions
(granted to HOSPITAL_ADMIN; RECEPTIONIST also gets link; SUPER_ADMIN gets
both), and enforces in the database that a patient has at most one link per
external system and that an ABHA number belongs to at most one patient.

Revision ID: f7a3d8c5e921
Revises: e5b7c2d94a16
Create Date: 2026-10-11 12:00:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f7a3d8c5e921'
down_revision: Union[str, None] = 'e5b7c2d94a16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (code, description, roles granted)
PERMISSIONS = [
    (
        "patients.link_abha",
        "Verify and link a patient's ABHA and record ABDM consent",
        ("SUPER_ADMIN", "HOSPITAL_ADMIN", "RECEPTIONIST"),
    ),
    ("patients.unlink_abha", "Unlink a patient's ABHA", ("SUPER_ADMIN", "HOSPITAL_ADMIN")),
]


def upgrade() -> None:
    connection = op.get_bind()
    for code, description, roles in PERMISSIONS:
        permission_id = str(uuid.uuid4())
        connection.execute(
            sa.text(
                """
                INSERT INTO permissions (id, code, module, description, created_at)
                VALUES (:id, :code, 'patients', :description, now())
                """
            ),
            {"id": permission_id, "code": code, "description": description},
        )
        connection.execute(
            sa.text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                SELECT r.id, :permission_id FROM roles r WHERE r.code = ANY(:roles)
                """
            ),
            {"permission_id": permission_id, "roles": list(roles)},
        )

    op.create_unique_constraint(
        'uq_patient_identity_links_patient_system', 'patient_identity_links', ['patient_id', 'system']
    )
    op.create_index(
        'uq_patient_identity_links_abha_number',
        'patient_identity_links',
        ['external_id'],
        unique=True,
        postgresql_where=sa.text("system = 'ABHA' AND external_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index('uq_patient_identity_links_abha_number', table_name='patient_identity_links')
    op.drop_constraint('uq_patient_identity_links_patient_system', 'patient_identity_links', type_='unique')

    codes = [code for code, _, _ in PERMISSIONS]
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code = ANY(:codes))"
        ),
        {"codes": codes},
    )
    connection.execute(sa.text("DELETE FROM permissions WHERE code = ANY(:codes)"), {"codes": codes})
