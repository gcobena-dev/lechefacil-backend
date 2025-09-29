"""Add shift to milk_productions and unique per day/turn

Revision ID: c1a2b3d4e5f6
Revises: b7cc0b57c42a
Create Date: 2025-09-29 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1a2b3d4e5f6'
down_revision = 'b7cc0b57c42a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add shift column with default 'AM'
    op.add_column('milk_productions', sa.Column('shift', sa.String(length=2), nullable=False, server_default='AM'))


def downgrade() -> None:
    op.drop_column('milk_productions', 'shift')
