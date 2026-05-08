"""Add name and location to tenant_configs

Revision ID: d8a9b7c6e5f1
Revises: 4d76d7417c55
Create Date: 2026-05-07 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd8a9b7c6e5f1'
down_revision: Union[str, Sequence[str], None] = '4d76d7417c55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tenant_configs",
        sa.Column("name", sa.String(length=120), nullable=True),
        schema="lechefacil",
    )
    op.execute("UPDATE lechefacil.tenant_configs SET name = 'Mi Finca' WHERE name IS NULL")
    op.alter_column(
        "tenant_configs",
        "name",
        existing_type=sa.String(length=120),
        nullable=False,
        schema="lechefacil",
    )
    op.add_column(
        "tenant_configs",
        sa.Column("location", sa.String(length=255), nullable=True),
        schema="lechefacil",
    )


def downgrade() -> None:
    op.drop_column("tenant_configs", "location", schema="lechefacil")
    op.drop_column("tenant_configs", "name", schema="lechefacil")
