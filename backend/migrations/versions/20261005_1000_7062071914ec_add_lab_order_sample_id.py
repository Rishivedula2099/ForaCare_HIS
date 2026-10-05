"""add lab_orders.sample_id

P6-B03: adds a nullable `lab_orders.sample_id` FK to `lab_samples` - set once
an order's tube is drawn/assigned under its accession
(`app/modules/lab/service.collect_sample`). Several `LabOrder`s sharing one
tube (e.g. LFT+LIPID off one red-top draw) share the same `sample_id`. This
is what lets a scanned tube barcode resolve back to the pending orders it
covers (`service.resolve_barcode`) before any `lab_results` row exists to
link them.

Revision ID: 7062071914ec
Revises: eeb5ef23008e
Create Date: 2026-10-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7062071914ec'
down_revision: Union[str, None] = 'eeb5ef23008e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('lab_orders', sa.Column('sample_id', sa.UUID(), nullable=True))
    op.create_foreign_key(
        op.f('fk_lab_orders_sample_id_lab_samples'),
        'lab_orders', 'lab_samples', ['sample_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint(op.f('fk_lab_orders_sample_id_lab_samples'), 'lab_orders', type_='foreignkey')
    op.drop_column('lab_orders', 'sample_id')
