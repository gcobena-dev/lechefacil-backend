"""Link an animal's sire to the reproduction catalog

Revision ID: f3b8d1e6c2a7
Revises: e7c3a9d2b1f4
Create Date: 2026-10-27 00:00:01.000000

A sire could only be a herd animal (`sire_id`) or free text
(`external_sire_code`), so bulls that only exist in the reproduction catalog
could not be linked from the genealogy. A herd bull that is also used as a
sire stays linked through `sire_catalog.animal_id`.

Existing free-text sires are linked when they match exactly one catalog bull
of the same farm by name, short code or registry code (case-insensitive).
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3b8d1e6c2a7"
down_revision: Union[str, Sequence[str], None] = "e7c3a9d2b1f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "animals",
        sa.Column("sire_catalog_id", sa.Uuid(as_uuid=True), nullable=True),
        schema="lechefacil",
    )
    op.create_foreign_key(
        "animals_sire_catalog_id_fkey",
        "animals",
        "sire_catalog",
        ["sire_catalog_id"],
        ["id"],
        source_schema="lechefacil",
        referent_schema="lechefacil",
    )
    op.execute(
        """
        WITH matches AS (
            SELECT a.id AS animal_id, min(s.id::text)::uuid AS sire_catalog_id
              FROM lechefacil.animals a
              JOIN lechefacil.sire_catalog s
                ON s.tenant_id = a.tenant_id
               AND s.deleted_at IS NULL
               AND lower(trim(a.external_sire_code)) IN (
                       lower(trim(s.name)),
                       lower(trim(coalesce(s.short_code, ''))),
                       lower(trim(coalesce(s.registry_code, '')))
                   )
             WHERE a.external_sire_code IS NOT NULL
               AND a.sire_id IS NULL
             GROUP BY a.id
            HAVING count(DISTINCT s.id) = 1
        )
        UPDATE lechefacil.animals a
           SET sire_catalog_id = m.sire_catalog_id
          FROM matches m
         WHERE a.id = m.animal_id
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        "animals_sire_catalog_id_fkey", "animals", schema="lechefacil", type_="foreignkey"
    )
    op.drop_column("animals", "sire_catalog_id", schema="lechefacil")
