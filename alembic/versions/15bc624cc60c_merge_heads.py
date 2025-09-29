"""merge heads

Revision ID: 15bc624cc60c
Revises: c1a2b3d4e5f6, ba7f3a1c1b20
Create Date: 2025-09-28 22:42:42.358497

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15bc624cc60c'
down_revision: Union[str, Sequence[str], None] = ('c1a2b3d4e5f6', 'ba7f3a1c1b20')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
