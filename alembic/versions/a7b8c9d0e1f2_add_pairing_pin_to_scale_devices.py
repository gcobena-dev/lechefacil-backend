"""add pairing_pin to scale_devices

Revision ID: a7b8c9d0e1f2
Revises: f1a2b3c4d5e6
Create Date: 2026-03-17 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "a7b8c9d0e1f2"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scale_devices",
        sa.Column("pairing_pin", sa.String(6), nullable=True),
        schema="lechefacil",
    )
    op.add_column(
        "scale_devices",
        sa.Column("pairing_pin_expires_at", sa.DateTime(timezone=True), nullable=True),
        schema="lechefacil",
    )
    op.create_index(
        "ix_scale_devices_pairing_pin",
        "scale_devices",
        ["pairing_pin"],
        schema="lechefacil",
    )


def downgrade() -> None:
    op.drop_index("ix_scale_devices_pairing_pin", table_name="scale_devices", schema="lechefacil")
    op.drop_column("scale_devices", "pairing_pin_expires_at", schema="lechefacil")
    op.drop_column("scale_devices", "pairing_pin", schema="lechefacil")
