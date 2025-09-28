"""add breed_variant to animals

Revision ID: ba7f3a1c1b20
Revises: 9c3d1b2a6a10
Create Date: 2025-09-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ba7f3a1c1b20'
down_revision: Union[str, Sequence[str], None] = '9c3d1b2a6a10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('animals', sa.Column('breed_variant', sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column('animals', 'breed_variant')

