"""add device_tokens table

Revision ID: d7e1b2a4c9f1
Revises: 0221fa8fd042
Create Date: 2025-10-08 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd7e1b2a4c9f1'
down_revision = '0221fa8fd042'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'device_tokens',
        sa.Column('id', sa.Uuid(), primary_key=True, nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('platform', sa.String(length=20), nullable=False),
        sa.Column('token', sa.String(length=512), nullable=False),
        sa.Column('app_version', sa.String(length=50), nullable=True),
        sa.Column('disabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('uq_device_tokens_token', 'device_tokens', ['token'], unique=True)
    op.create_index('ix_device_tokens_user', 'device_tokens', ['user_id'], unique=False)
    op.create_index('ix_device_tokens_tenant', 'device_tokens', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_device_tokens_tenant', table_name='device_tokens')
    op.drop_index('ix_device_tokens_user', table_name='device_tokens')
    op.drop_index('uq_device_tokens_token', table_name='device_tokens')
    op.drop_table('device_tokens')

