"""add user_sessions, otp_challenges, role numeric_code, user security fields

Closes out the Phase 1 security gate items: replaces the ad-hoc
`refresh_tokens` table (which tracked only a token hash, no reuse/session
lineage) with `user_sessions` (adds family_id, facility_id, ip/user-agent,
status - see app/modules/auth/service.py::rotate_session for the reuse
detection this backs), adds `otp_challenges` for the email/phone change
flow, adds `phone`/verification/`last_login_at` to `users`, and adds a
stable integer `roles.numeric_code` alongside the existing string `code`
key and `name` label (P1-B07 role review).

Revision ID: 7d2f9a41c6b3
Revises: 9657dbf2d9f8
Create Date: 2026-09-16 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.modules.rbac.constants import SYSTEM_ROLE_NUMERIC_CODES

# revision identifiers, used by Alembic.
revision: str = '7d2f9a41c6b3'
down_revision: Union[str, None] = '9657dbf2d9f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('refresh_tokens')

    op.create_table(
        'user_sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('facility_id', sa.UUID(), nullable=False),
        sa.Column('refresh_token_jti_hash', sa.String(length=64), nullable=False),
        sa.Column('family_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(['facility_id'], ['facilities.id'], name=op.f('fk_user_sessions_facility_id_facilities')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_user_sessions_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_sessions')),
        sa.UniqueConstraint('refresh_token_jti_hash', name=op.f('uq_user_sessions_refresh_token_jti_hash')),
    )
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'])
    op.create_index(op.f('ix_user_sessions_family_id'), 'user_sessions', ['family_id'])

    op.create_table(
        'otp_challenges',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('purpose', sa.String(length=30), nullable=False),
        sa.Column('target_value', sa.String(length=255), nullable=False),
        sa.Column('code_hash', sa.String(length=64), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('max_attempts', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_otp_challenges_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_otp_challenges')),
    )
    op.create_index(
        op.f('ix_otp_challenges_user_id_purpose_target_value'),
        'otp_challenges',
        ['user_id', 'purpose', 'target_value'],
    )

    op.add_column('users', sa.Column('phone', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('email_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('phone_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True))
    op.create_unique_constraint(op.f('uq_users_phone'), 'users', ['phone'])

    op.add_column('roles', sa.Column('numeric_code', sa.Integer(), nullable=True))
    connection = op.get_bind()
    for code, numeric_code in SYSTEM_ROLE_NUMERIC_CODES.items():
        connection.execute(
            sa.text("UPDATE roles SET numeric_code = :numeric_code WHERE code = :code"),
            {"numeric_code": numeric_code, "code": code},
        )
    op.alter_column('roles', 'numeric_code', nullable=False)
    op.create_unique_constraint(op.f('uq_roles_numeric_code'), 'roles', ['numeric_code'])


def downgrade() -> None:
    op.drop_constraint(op.f('uq_roles_numeric_code'), 'roles', type_='unique')
    op.drop_column('roles', 'numeric_code')

    op.drop_constraint(op.f('uq_users_phone'), 'users', type_='unique')
    op.drop_column('users', 'last_login_at')
    op.drop_column('users', 'phone_verified_at')
    op.drop_column('users', 'email_verified_at')
    op.drop_column('users', 'phone')

    op.drop_index(op.f('ix_otp_challenges_user_id_purpose_target_value'), table_name='otp_challenges')
    op.drop_table('otp_challenges')

    op.drop_index(op.f('ix_user_sessions_family_id'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_user_id'), table_name='user_sessions')
    op.drop_table('user_sessions')

    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_refresh_tokens_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_refresh_tokens')),
        sa.UniqueConstraint('token_hash', name=op.f('uq_refresh_tokens_token_hash')),
    )
