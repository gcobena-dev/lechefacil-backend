"""Add delivery and production unit columns to tenant_configs

Revision ID: 8e5a2a1d9c3b
Revises: b7cc0b57c42a
Create Date: 2025-09-22 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e5a2a1d9c3b'
down_revision: Union[str, Sequence[str], None] = 'b7cc0b57c42a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # This migration is now a no-op as the changes were incorporated into the initial migration
    pass


def downgrade() -> None:
    # This migration is now a no-op
    pass

