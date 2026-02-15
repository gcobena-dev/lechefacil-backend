"""Add reproduction tables (sire_catalog, semen_inventory, inseminations)

Revision ID: a1b2c3d4e5f6
Revises: 191b90d7ae01
Create Date: 2026-02-13 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '191b90d7ae01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sire_catalog, semen_inventory, and inseminations tables."""

    # --- sire_catalog ---
    op.create_table(
        'sire_catalog',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('short_code', sa.String(length=64), nullable=True),
        sa.Column('registry_code', sa.String(length=128), nullable=True),
        sa.Column('registry_name', sa.String(length=128), nullable=True),
        sa.Column('breed_id', sa.Uuid(), nullable=True),
        sa.Column('animal_id', sa.Uuid(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('genetic_notes', sa.Text(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_sire_catalog_tenant_id', 'sire_catalog', ['tenant_id'],
        unique=False,
    )
    op.create_index(
        'ux_sire_catalog_tenant_registry',
        'sire_catalog',
        ['tenant_id', 'registry_code'],
        unique=True,
        postgresql_where="registry_code IS NOT NULL AND deleted_at IS NULL",
    )

    # --- semen_inventory ---
    op.create_table(
        'semen_inventory',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('sire_catalog_id', sa.Uuid(), nullable=False),
        sa.Column('batch_code', sa.String(length=128), nullable=True),
        sa.Column('tank_id', sa.String(length=64), nullable=True),
        sa.Column('canister_position', sa.String(length=64), nullable=True),
        sa.Column('initial_quantity', sa.Integer(), nullable=False),
        sa.Column('current_quantity', sa.Integer(), nullable=False),
        sa.Column('supplier', sa.String(length=255), nullable=True),
        sa.Column('cost_per_straw', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('currency', sa.String(length=3), server_default='USD', nullable=False),
        sa.Column('purchase_date', sa.Date(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(
            ['sire_catalog_id'], ['sire_catalog.id'],
            name='fk_semen_inventory_sire',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_semen_inventory_tenant_sire', 'semen_inventory',
        ['tenant_id', 'sire_catalog_id'],
        unique=False,
    )
    op.create_index(
        'ix_semen_inventory_tenant_stock', 'semen_inventory',
        ['tenant_id', 'current_quantity'],
        unique=False,
        postgresql_where='current_quantity > 0 AND deleted_at IS NULL',
    )

    # --- inseminations ---
    op.create_table(
        'inseminations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('animal_id', sa.Uuid(), nullable=False),
        sa.Column('sire_catalog_id', sa.Uuid(), nullable=True),
        sa.Column('semen_inventory_id', sa.Uuid(), nullable=True),
        sa.Column('service_event_id', sa.Uuid(), nullable=True),
        sa.Column('service_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('method', sa.String(length=16), nullable=False),
        sa.Column('technician', sa.String(length=255), nullable=True),
        sa.Column('straw_count', sa.Integer(), server_default='1', nullable=False),
        sa.Column('heat_detected', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('protocol', sa.String(length=128), nullable=True),
        sa.Column('pregnancy_status', sa.String(length=16), server_default="'PENDING'", nullable=False),
        sa.Column('pregnancy_check_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pregnancy_checked_by', sa.String(length=255), nullable=True),
        sa.Column('expected_calving_date', sa.Date(), nullable=True),
        sa.Column('calving_event_id', sa.Uuid(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(
            ['sire_catalog_id'], ['sire_catalog.id'],
            name='fk_inseminations_sire',
        ),
        sa.ForeignKeyConstraint(
            ['semen_inventory_id'], ['semen_inventory.id'],
            name='fk_inseminations_semen',
        ),
        sa.ForeignKeyConstraint(
            ['animal_id'], ['animals.id'],
            name='fk_inseminations_animal',
        ),
        sa.ForeignKeyConstraint(
            ['service_event_id'], ['animal_events.id'],
            name='fk_inseminations_service_event',
        ),
        sa.ForeignKeyConstraint(
            ['calving_event_id'], ['animal_events.id'],
            name='fk_inseminations_calving_event',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_inseminations_tenant_animal_date', 'inseminations',
        ['tenant_id', 'animal_id', 'service_date'],
        unique=False,
    )
    op.create_index(
        'ix_inseminations_tenant_sire', 'inseminations',
        ['tenant_id', 'sire_catalog_id'],
        unique=False,
    )
    op.create_index(
        'ix_inseminations_pending', 'inseminations',
        ['tenant_id', 'pregnancy_status', 'service_date'],
        unique=False,
        postgresql_where="pregnancy_status = 'PENDING' AND deleted_at IS NULL",
    )


def downgrade() -> None:
    """Drop reproduction tables."""
    op.drop_index('ix_inseminations_pending', table_name='inseminations')
    op.drop_index('ix_inseminations_tenant_sire', table_name='inseminations')
    op.drop_index('ix_inseminations_tenant_animal_date', table_name='inseminations')
    op.drop_table('inseminations')

    op.drop_index('ix_semen_inventory_tenant_stock', table_name='semen_inventory')
    op.drop_index('ix_semen_inventory_tenant_sire', table_name='semen_inventory')
    op.drop_table('semen_inventory')

    op.drop_index('ux_sire_catalog_tenant_registry', table_name='sire_catalog')
    op.drop_index('ix_sire_catalog_tenant_id', table_name='sire_catalog')
    op.drop_table('sire_catalog')
