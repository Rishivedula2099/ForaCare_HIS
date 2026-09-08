"""add roles, permissions, role_permissions tables

Adds the RBAC schema (Role, Permission, Role<->Permission mapping) and a
nullable `users.role_id` FK. The next migration seeds this data, backfills
`role_id` from the legacy `role` enum column, and drops that column.

Revision ID: d4b2e6a91f03
Revises: cc810724b198
Create Date: 2026-09-08 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd4b2e6a91f03'
down_revision: Union[str, None] = 'cc810724b198'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'roles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_roles')),
        sa.UniqueConstraint('code', name=op.f('uq_roles_code')),
    )
    op.create_table(
        'permissions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('module', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_permissions')),
        sa.UniqueConstraint('code', name=op.f('uq_permissions_code')),
    )
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.UUID(), nullable=False),
        sa.Column('permission_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ['permission_id'], ['permissions.id'], name=op.f('fk_role_permissions_permission_id_permissions')
        ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], name=op.f('fk_role_permissions_role_id_roles')),
        sa.PrimaryKeyConstraint('role_id', 'permission_id', name=op.f('pk_role_permissions')),
    )
    op.add_column('users', sa.Column('role_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f('fk_users_role_id_roles'), 'users', 'roles', ['role_id'], ['id']
    )


def downgrade() -> None:
    op.drop_constraint(op.f('fk_users_role_id_roles'), 'users', type_='foreignkey')
    op.drop_column('users', 'role_id')
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    op.drop_table('roles')
