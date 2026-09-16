"""merge audit and patient branches

Both `add_audit_logs_table` (58a45564ebbe's ancestor chain) and
`add_patient_tables` branched off the same parent (e7c1f4a2b856), producing
two independent heads. This merge revision has no schema changes of its own
- it only unifies the graph so `alembic upgrade head` has a single target.

Revision ID: c340fcb4ffa0
Revises: 58a45564ebbe, b8d1e4f6a209
Create Date: 2026-09-15 14:31:19.283575

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c340fcb4ffa0'
down_revision: Union[str, None] = ('58a45564ebbe', 'b8d1e4f6a209')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
