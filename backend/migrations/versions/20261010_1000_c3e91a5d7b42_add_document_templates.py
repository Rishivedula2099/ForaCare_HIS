"""add document templates and versions

P7-B02: `document_templates` (one mutable pointer row per facility and
document type) and `document_template_versions` (immutable V1/V2/V3
snapshots, so a historical document can be reproduced from the exact layout
it was generated with). Also adds the `documents.manage_templates`
permission, granted to SUPER_ADMIN and HOSPITAL_ADMIN.

Revision ID: c3e91a5d7b42
Revises: 084f648c19a9
Create Date: 2026-10-10 10:00:00.000000

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3e91a5d7b42'
down_revision: Union[str, None] = '084f648c19a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSION_CODE = "documents.manage_templates"
GRANTED_ROLES = ("SUPER_ADMIN", "HOSPITAL_ADMIN")


def upgrade() -> None:
    op.create_table(
        'document_templates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tenant_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('active_version_number', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], name=op.f('fk_document_templates_tenant_id_tenants')),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_document_templates_facility_id_facilities')),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_document_templates_created_by_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_document_templates')),
        sa.UniqueConstraint('facility_id', 'document_type', name='uq_document_templates_facility_type'),
    )

    op.create_table(
        'document_template_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('template_id', sa.UUID(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('paper_size', sa.String(length=20), nullable=False),
        sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('change_note', sa.String(length=500), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['document_templates.id'], name=op.f('fk_document_template_versions_template_id_document_templates')),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_document_template_versions_created_by_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_document_template_versions')),
        sa.UniqueConstraint('template_id', 'version_number', name='uq_document_template_versions_number'),
    )
    op.create_index(op.f('ix_document_template_versions_template_id'), 'document_template_versions', ['template_id'])

    connection = op.get_bind()
    permission_id = str(uuid.uuid4())
    connection.execute(
        sa.text(
            """
            INSERT INTO permissions (id, code, module, description, created_at)
            VALUES (:id, :code, 'documents', 'Create, version, and activate document templates', now())
            """
        ),
        {"id": permission_id, "code": PERMISSION_CODE},
    )
    connection.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, :permission_id FROM roles r WHERE r.code = ANY(:roles)
            """
        ),
        {"permission_id": permission_id, "roles": list(GRANTED_ROLES)},
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN (SELECT id FROM permissions WHERE code = :code)"
        ),
        {"code": PERMISSION_CODE},
    )
    connection.execute(sa.text("DELETE FROM permissions WHERE code = :code"), {"code": PERMISSION_CODE})
    op.drop_index(op.f('ix_document_template_versions_template_id'), table_name='document_template_versions')
    op.drop_table('document_template_versions')
    op.drop_table('document_templates')
