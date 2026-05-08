"""Add is_super_admin to users and create access_requests table

Revision ID: c5e3f2a1b9d4
Revises: d8a9b7c6e5f1
Create Date: 2026-05-07 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c5e3f2a1b9d4'
down_revision: Union[str, Sequence[str], None] = 'd8a9b7c6e5f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_super_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        schema="lechefacil",
    )
    op.execute(
        "UPDATE lechefacil.users SET is_super_admin = true WHERE email = 'gcobena.dev@gmail.com'"
    )

    op.create_table(
        "access_requests",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("requester_user_id", sa.Uuid(), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone_number", sa.String(length=50), nullable=True),
        sa.Column("farm_name", sa.String(length=120), nullable=False),
        sa.Column("farm_location", sa.String(length=255), nullable=True),
        sa.Column("requested_role", sa.String(length=50), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column("decided_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.Column("created_tenant_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["requester_user_id"],
            ["lechefacil.users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["decided_by_user_id"],
            ["lechefacil.users.id"],
            ondelete="SET NULL",
        ),
        schema="lechefacil",
    )
    op.create_index(
        "ix_access_requests_status",
        "access_requests",
        ["status"],
        schema="lechefacil",
    )
    # Postgres partial unique index: at most one pending request per email
    op.execute(
        "CREATE UNIQUE INDEX uq_access_requests_pending_email "
        "ON lechefacil.access_requests (email) WHERE status = 'pending'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS lechefacil.uq_access_requests_pending_email")
    op.drop_index("ix_access_requests_status", table_name="access_requests", schema="lechefacil")
    op.drop_table("access_requests", schema="lechefacil")
    op.drop_column("users", "is_super_admin", schema="lechefacil")
