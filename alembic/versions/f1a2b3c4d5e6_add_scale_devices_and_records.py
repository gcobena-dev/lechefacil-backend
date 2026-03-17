"""add scale_devices and scale_device_records

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-03-16 22:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = "f1a2b3c4d5e6"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scale_devices",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("api_key", sa.String(64), nullable=False),
        sa.Column("wifi_ssid", sa.String(64), nullable=True),
        sa.Column("wifi_password", sa.String(128), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("firmware_version", sa.String(20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="lechefacil",
    )
    op.create_index(
        "ix_scale_devices_tenant_id",
        "scale_devices",
        ["tenant_id"],
        schema="lechefacil",
    )
    op.create_index(
        "ix_scale_devices_api_key",
        "scale_devices",
        ["api_key"],
        unique=True,
        schema="lechefacil",
    )

    op.create_table(
        "scale_device_records",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.Uuid(), nullable=False),
        sa.Column("device_record_id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(50), nullable=False),
        sa.Column("peso", sa.DECIMAL(12, 3), nullable=False),
        sa.Column("fecha", sa.String(10), nullable=False),
        sa.Column("hora", sa.String(8), nullable=False),
        sa.Column("turno", sa.String(2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("matched_animal_id", sa.Uuid(), nullable=True),
        sa.Column("milk_production_id", sa.Uuid(), nullable=True),
        sa.Column("batch_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="lechefacil",
    )
    op.create_index(
        "ix_scale_device_records_tenant_id",
        "scale_device_records",
        ["tenant_id"],
        schema="lechefacil",
    )
    op.create_index(
        "ix_scale_device_records_device_id",
        "scale_device_records",
        ["device_id"],
        schema="lechefacil",
    )
    op.create_index(
        "ix_scale_device_records_batch_id",
        "scale_device_records",
        ["batch_id"],
        schema="lechefacil",
    )
    op.create_index(
        "ix_scale_device_records_tenant_batch",
        "scale_device_records",
        ["tenant_id", "batch_id"],
        schema="lechefacil",
    )
    op.create_index(
        "ix_scale_device_records_tenant_status",
        "scale_device_records",
        ["tenant_id", "status"],
        schema="lechefacil",
    )
    op.create_index(
        "ix_scale_device_records_device_record",
        "scale_device_records",
        ["device_id", "device_record_id"],
        schema="lechefacil",
    )


def downgrade() -> None:
    op.drop_index("ix_scale_device_records_device_record", table_name="scale_device_records", schema="lechefacil")
    op.drop_index("ix_scale_device_records_tenant_status", table_name="scale_device_records", schema="lechefacil")
    op.drop_index("ix_scale_device_records_tenant_batch", table_name="scale_device_records", schema="lechefacil")
    op.drop_index("ix_scale_device_records_batch_id", table_name="scale_device_records", schema="lechefacil")
    op.drop_index("ix_scale_device_records_device_id", table_name="scale_device_records", schema="lechefacil")
    op.drop_index("ix_scale_device_records_tenant_id", table_name="scale_device_records", schema="lechefacil")
    op.drop_table("scale_device_records", schema="lechefacil")
    op.drop_index("ix_scale_devices_api_key", table_name="scale_devices", schema="lechefacil")
    op.drop_index("ix_scale_devices_tenant_id", table_name="scale_devices", schema="lechefacil")
    op.drop_table("scale_devices", schema="lechefacil")
