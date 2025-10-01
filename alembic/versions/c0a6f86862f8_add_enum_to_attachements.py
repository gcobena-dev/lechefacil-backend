"""Add enum to attachements

Revision ID: c0a6f86862f8
Revises: 15bc624cc60c
Create Date: 2025-10-01 12:04:45.103103

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c0a6f86862f8'
down_revision: Union[str, Sequence[str], None] = '15bc624cc60c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Only change owner_type to enum in attachments table
    # Add new enum value MILK_PRODUCTION_OCR
    op.alter_column('attachments', 'owner_type',
               existing_type=sa.VARCHAR(length=50),
               type_=sa.Enum('ANIMAL', 'HEALTH_EVENT', 'MILK_PRODUCTION_OCR', name='ownertype', native_enum=False),
               existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert owner_type back to VARCHAR
    op.alter_column('attachments', 'owner_type',
               existing_type=sa.Enum('ANIMAL', 'HEALTH_EVENT', 'MILK_PRODUCTION_OCR', name='ownertype', native_enum=False),
               type_=sa.VARCHAR(length=50),
               existing_nullable=False)
