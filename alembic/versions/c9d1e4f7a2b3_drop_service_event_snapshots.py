"""Drop the copied service values from SERVICE animal_events

Revision ID: c9d1e4f7a2b3
Revises: b7f4c9e2d1a8
Create Date: 2026-09-12 00:00:00.000000

A service was written twice: the record in `inseminations` and a flattened copy
in the SERVICE event's `data`. Only the record was updated on edit, so the
animal's timeline kept showing the bull, method and technician the service was
created with while /reproduction showed the current ones.

The timeline now reads those values from `inseminations` on every request, so
the copy is dead weight that only invites the two to disagree again. It is
removed here for every SERVICE event that has a live insemination behind it —
every value dropped is still on that record.

Events with no insemination (imported herds, events predating the reproduction
module) are left untouched: there `data` is the service itself, not a copy.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9d1e4f7a2b3"
down_revision: Union[str, Sequence[str], None] = "b7f4c9e2d1a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


COPIED_KEYS = (
    "method",
    "technician",
    "sire_name",
    "sire_code",
    "sire_catalog_id",
    "external_sire_code",
    "external_sire_registry",
)


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    # Tables are schema-qualified on purpose: the search_path of the role that
    # runs the migrations does not always include `lechefacil`, and an
    # unqualified name fails with "relation animal_events does not exist".
    # `scripts/start.sh` runs `alembic upgrade head` under `set -e`, so that
    # failure stops the container from starting at all.
    #
    # `data` is a plain JSON column, so it is cast to jsonb to subtract the keys
    # and cast back. Keys the event does not have are a no-op.
    conn.execute(
        sa.text(
            """
            UPDATE lechefacil.animal_events ae
               SET data = ((ae.data::jsonb) - CAST(:keys AS text[]))::json
             WHERE ae.type IN ('SERVICE', 'EMBRYO_TRANSFER')
               AND ae.data IS NOT NULL
               AND EXISTS (
                     SELECT 1 FROM lechefacil.inseminations i
                      WHERE i.service_event_id = ae.id
                        AND i.deleted_at IS NULL
                   )
            """
        ),
        {"keys": list(COPIED_KEYS)},
    )


def downgrade() -> None:
    """Put the values back from the record they were copied from."""
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    conn.execute(
        sa.text(
            """
            UPDATE lechefacil.animal_events ae
               SET data = (
                     COALESCE(ae.data::jsonb, '{}'::jsonb)
                     || jsonb_strip_nulls(
                          jsonb_build_object(
                            'method', i.method,
                            'technician', i.technician,
                            'sire_catalog_id', sc.id::text,
                            'sire_name', sc.name,
                            'sire_code', COALESCE(sc.short_code, sc.registry_code)
                          )
                        )
                   )::json
              FROM lechefacil.inseminations i
              LEFT JOIN lechefacil.sire_catalog sc ON sc.id = i.sire_catalog_id
             WHERE i.service_event_id = ae.id
               AND i.deleted_at IS NULL
               AND ae.type IN ('SERVICE', 'EMBRYO_TRANSFER')
            """
        )
    )
