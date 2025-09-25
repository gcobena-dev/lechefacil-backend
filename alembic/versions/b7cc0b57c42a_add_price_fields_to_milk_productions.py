"""Add price fields to milk_productions

Revision ID: b7cc0b57c42a
Revises: 06da90558885
Create Date: 2025-09-21 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7cc0b57c42a'
down_revision: Union[str, Sequence[str], None] = '06da90558885'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('milk_productions', sa.Column('buyer_id', sa.Uuid(), nullable=True))
    op.add_column('milk_productions', sa.Column('price_snapshot', sa.DECIMAL(precision=10, scale=4), nullable=True))
    op.add_column('milk_productions', sa.Column('currency', sa.String(length=8), nullable=False, server_default='USD'))
    op.add_column('milk_productions', sa.Column('amount', sa.DECIMAL(precision=12, scale=2), nullable=True))


def downgrade() -> None:
    op.drop_column('milk_productions', 'amount')
    op.drop_column('milk_productions', 'currency')
    op.drop_column('milk_productions', 'price_snapshot')
    op.drop_column('milk_productions', 'buyer_id')

