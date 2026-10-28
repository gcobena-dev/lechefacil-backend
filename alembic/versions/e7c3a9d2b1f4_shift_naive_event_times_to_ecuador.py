"""Shift animal event times that were stored 5 hours early

Revision ID: e7c3a9d2b1f4
Revises: d4b8e1c7f905
Create Date: 2026-10-27 00:00:00.000000

The event form sends what the user typed ("2026-10-22T00:30") without an
offset, and the API read it as UTC. Every event registered from that form was
stored 5 hours early: a calving typed at 00:30 showed up as 19:30 of the
previous day. The API now reads naive values as Ecuador time, so the existing
rows are moved forward to match.

Only events created from that form are shifted. SERVICE events are created by
the insemination endpoint, whose form sends a real UTC timestamp.

Dates derived from those events (lactation start/end, calf birth date) were
taken from the naive value itself, so they are already the day the user meant
and are left untouched. The sale/death/cull date copied to the animal is a
timestamp, so it moves with its event.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7c3a9d2b1f4"
down_revision: Union[str, Sequence[str], None] = "d4b8e1c7f905"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Ecuador has no daylight saving time.
OFFSET = "interval '5 hours'"


def _shift(sign: str) -> None:
    # Disposition first: it is matched against the event's current value.
    op.execute(
        f"""
        UPDATE lechefacil.animals a
           SET disposition_at = a.disposition_at {sign} {OFFSET}
          FROM lechefacil.animal_events e
         WHERE e.animal_id = a.id
           AND e.type IN ('SALE', 'DEATH', 'CULL')
           AND a.disposition_at = e.occurred_at
        """
    )
    op.execute(
        f"""
        UPDATE lechefacil.animal_events
           SET occurred_at = occurred_at {sign} {OFFSET}
         WHERE type <> 'SERVICE'
        """
    )


def upgrade() -> None:
    _shift("+")


def downgrade() -> None:
    # Also moves back events registered after the upgrade, which were stored
    # correctly; only use it right after a failed deploy.
    _shift("-")
