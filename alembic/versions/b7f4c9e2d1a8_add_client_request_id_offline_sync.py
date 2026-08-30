"""Add client_request_id to milk records and enforce production uniqueness

Supports the offline outbox: the device generates client_request_id, so
replaying a queued write returns the original record instead of duplicating it.
Also promotes the application-level "one production per animal/day/shift" check
to a real partial unique index — that check was racy, and sync makes concurrent
writes (two phones uploading the same milking) much more likely.

Revision ID: b7f4c9e2d1a8
Revises: c5e3f2a1b9d4
Create Date: 2026-08-29 17:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b7f4c9e2d1a8'
down_revision: Union[str, Sequence[str], None] = 'c5e3f2a1b9d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SCHEMA = "lechefacil"


def upgrade() -> None:
    for table in ("milk_productions", "milk_deliveries"):
        op.add_column(
            table,
            sa.Column("client_request_id", sa.Uuid(as_uuid=True), nullable=True),
            schema=SCHEMA,
        )
        # Partial: rows created before this (and any created online without an
        # id) stay NULL, and NULLs must not collide with each other.
        op.create_index(
            f"uq_{table}_client_request",
            table,
            ["tenant_id", "client_request_id"],
            unique=True,
            postgresql_where=sa.text("client_request_id IS NOT NULL"),
            schema=SCHEMA,
        )

    # The natural-key index is defence in depth: the router already rejects
    # duplicates. Legacy rows may violate it, and this migration runs on
    # container start under `set -e` — so failing here would take the API down
    # rather than deploy. Skip loudly instead, and let it be added once the data
    # is clean.
    duplicates = (
        op.get_bind()
        .execute(
            sa.text(
                f"""
                SELECT count(*) FROM (
                    SELECT 1 FROM {SCHEMA}.milk_productions
                    WHERE deleted_at IS NULL AND animal_id IS NOT NULL
                    GROUP BY tenant_id, animal_id, date, shift
                    HAVING count(*) > 1
                ) d
                """
            )
        )
        .scalar()
    )
    if duplicates:
        print(
            f"WARNING: {duplicates} duplicate (tenant, animal, date, shift) groups found; "
            "skipping uq_milk_productions_animal_date_shift. Clean them up and create "
            "the index manually."
        )
    else:
        op.create_index(
            "uq_milk_productions_animal_date_shift",
            "milk_productions",
            ["tenant_id", "animal_id", "date", "shift"],
            unique=True,
            postgresql_where=sa.text("deleted_at IS NULL AND animal_id IS NOT NULL"),
            schema=SCHEMA,
        )


def downgrade() -> None:
    # May never have been created (see upgrade), so this must be tolerant.
    op.execute(f"DROP INDEX IF EXISTS {SCHEMA}.uq_milk_productions_animal_date_shift")
    for table in ("milk_productions", "milk_deliveries"):
        op.drop_index(
            f"uq_{table}_client_request", table_name=table, schema=SCHEMA
        )
        op.drop_column(table, "client_request_id", schema=SCHEMA)
