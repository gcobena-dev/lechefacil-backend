"""add breeds and lots tables, add breed_id/current_lot_id to animals

Revision ID: 9c3d1b2a6a10
Revises: 75f4082d1def
Create Date: 2025-09-28 00:00:00.000000

"""
from typing import Sequence, Union
import json
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision: str = '9c3d1b2a6a10'
down_revision: Union[str, Sequence[str], None] = '75f4082d1def'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create breeds
    op.create_table(
        'breeds',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('is_system_default', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('metadata', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_breeds_tenant_id'), 'breeds', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_breeds_name'), 'breeds', ['name'], unique=False)
    op.create_index(op.f('ix_breeds_code'), 'breeds', ['code'], unique=False)

    # Seed default breeds (system defaults)
    connection = op.get_bind()
    default_breeds = [
        {"code": "HOLSTEIN", "name": "Holstein"},
        {"code": "JERSEY", "name": "Jersey"},
        {"code": "BROWN_SWISS", "name": "Pardo Suizo"},
        {"code": "NORMANDE", "name": "Normando"},
        {"code": "MONTBELIARDE", "name": "Montbéliarde"},
        {"code": "GIR", "name": "Gyr Lechero"},
        {"code": "GUZERAT", "name": "Guzerat"},
        {"code": "GIROLANDO", "name": "Girolando"},
        {"code": "SIMMENTAL", "name": "Simmental"},
        {"code": "SIMBRAH", "name": "Simbrah"},
        {"code": "BRAHMAN", "name": "Brahman"},
        {"code": "ANGUS", "name": "Angus"},
        {"code": "BRANGUS", "name": "Brangus"},
        {"code": "NELORE", "name": "Nelore"},
        {"code": "BEEFMASTER", "name": "Beefmaster"},
        {"code": "BRAFORD", "name": "Braford"},
        {"code": "CHAROLAIS", "name": "Charolais"},
        {"code": "SANTA_GERTRUDIS", "name": "Santa Gertrudis"},
        {"code": "CRIOLLA", "name": "Criolla"},
    ]
    for b in default_breeds:
        connection.execute(
            sa.text(
                """
                INSERT INTO breeds (id, tenant_id, name, code, is_system_default, active, created_at)
                VALUES (:id, NULL, :name, :code, TRUE, TRUE, NOW())
                """
            ),
            {"id": str(uuid4()), "name": b["name"], "code": b["code"]},
        )

    # Create lots
    op.create_table(
        'lots',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('notes', sa.String(length=1024), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'name', name='ux_lots_tenant_name')
    )
    op.create_index(op.f('ix_lots_tenant_id'), 'lots', ['tenant_id'], unique=False)

    # Add FKs (nullable) to animals for backward compat
    op.add_column('animals', sa.Column('breed_id', sa.Uuid(), nullable=True))
    op.add_column('animals', sa.Column('current_lot_id', sa.Uuid(), nullable=True))


def downgrade() -> None:
    op.drop_column('animals', 'current_lot_id')
    op.drop_column('animals', 'breed_id')
    op.drop_index(op.f('ix_lots_tenant_id'), table_name='lots')
    op.drop_table('lots')
    op.drop_index(op.f('ix_breeds_code'), table_name='breeds')
    op.drop_index(op.f('ix_breeds_name'), table_name='breeds')
    op.drop_index(op.f('ix_breeds_tenant_id'), table_name='breeds')
    op.drop_table('breeds')
