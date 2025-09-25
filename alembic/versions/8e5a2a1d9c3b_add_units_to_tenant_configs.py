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
    # Add new unit columns with sensible defaults
    op.add_column('tenant_configs', sa.Column('default_delivery_input_unit', sa.String(length=8), nullable=False, server_default='l'))
    op.add_column('tenant_configs', sa.Column('default_production_input_unit', sa.String(length=8), nullable=False, server_default='lb'))

    # Migrate data from old default_input_unit if present (map to production unit)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='tenant_configs' AND column_name='default_input_unit'
            ) THEN
                UPDATE tenant_configs
                SET default_production_input_unit = COALESCE(NULLIF(default_input_unit, ''), 'lb');
            END IF;
        END
        $$;
        """
    )

    # Remove server defaults to let application control values
    with op.batch_alter_table('tenant_configs') as batch_op:
        batch_op.alter_column('default_delivery_input_unit', server_default=None)
        batch_op.alter_column('default_production_input_unit', server_default=None)


def downgrade() -> None:
    with op.batch_alter_table('tenant_configs') as batch_op:
        batch_op.drop_column('default_production_input_unit')
        batch_op.drop_column('default_delivery_input_unit')

