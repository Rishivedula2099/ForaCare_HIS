"""P10-B01/F01: facility memberships, activation/reset tokens, onboarding requests

Revision ID: a1b2c3d4e5f6
Revises: f7a3d8c5e921
Create Date: 2026-10-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f7a3d8c5e921"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_facility_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_user_facility_memberships_user_id_users")),
        sa.ForeignKeyConstraint(
            ["facility_id"], ["facilities.id"], name=op.f("fk_user_facility_memberships_facility_id_facilities")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_facility_memberships")),
        sa.UniqueConstraint("user_id", "facility_id", name="uq_user_facility_memberships_user_facility"),
    )
    op.create_index(op.f("ix_user_facility_memberships_user_id"), "user_facility_memberships", ["user_id"])
    # Every existing user keeps working: their home facility becomes the
    # default membership.
    op.execute(
        """
        INSERT INTO user_facility_memberships (id, user_id, facility_id, is_default, created_at)
        SELECT gen_random_uuid(), id, facility_id, true, now() FROM users
        """
    )

    op.create_table(
        "user_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purpose", sa.String(length=20), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_user_tokens_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_user_tokens_token_hash")),
    )
    op.create_index(op.f("ix_user_tokens_user_id"), "user_tokens", ["user_id"])

    op.create_table(
        "onboarding_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_name", sa.String(length=255), nullable=False),
        sa.Column("contact_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("facility_type", sa.String(length=50), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="NEW"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_onboarding_requests")),
    )


def downgrade() -> None:
    op.drop_table("onboarding_requests")
    op.drop_index(op.f("ix_user_tokens_user_id"), table_name="user_tokens")
    op.drop_table("user_tokens")
    op.drop_index(op.f("ix_user_facility_memberships_user_id"), table_name="user_facility_memberships")
    op.drop_table("user_facility_memberships")
