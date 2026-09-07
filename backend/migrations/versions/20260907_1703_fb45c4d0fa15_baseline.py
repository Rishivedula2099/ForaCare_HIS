"""baseline

Establishes the Alembic version history for the project. No schema changes
yet - domain models land in their own migrations starting with Phase 2
(Patient master).

Revision ID: fb45c4d0fa15
Revises:
Create Date: 2026-09-07 17:03:51.188088

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fb45c4d0fa15'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
