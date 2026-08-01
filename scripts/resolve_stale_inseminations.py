#!/usr/bin/env python3
"""
Settle services that were left PENDING even though the cow already calved.

Before the calving handler learned to close the cycle it ended, a service whose
pregnancy check was never registered stayed PENDING forever, so the cow kept
showing up as "Inseminada" on /reproduction long after her calving. This script
applies the same rule retroactively to existing records:

- the most recent PENDING service compatible with the gestation length
  (240-310 days before the calving) is credited with the pregnancy: CONFIRMED
  and linked to the calving event;
- every other PENDING service registered before that calving is closed as OPEN.

Usage:
  python scripts/resolve_stale_inseminations.py --dry-run   # report only
  python scripts/resolve_stale_inseminations.py             # apply changes
  python scripts/resolve_stale_inseminations.py --tenant-id UUID
"""

import argparse
import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select

from src.application.use_cases.animals.register_event import (
    MAX_GESTATION_DAYS,
    MIN_GESTATION_DAYS,
)
from src.config.settings import get_settings
from src.domain.models.insemination import PregnancyStatus
from src.infrastructure.db.orm.animal import AnimalORM
from src.infrastructure.db.orm.animal_event import AnimalEventORM
from src.infrastructure.db.orm.insemination import InseminationORM
from src.infrastructure.db.session import create_engine, create_session_factory


async def resolve(tenant_id: UUID | None, dry_run: bool) -> None:
    engine = create_engine(get_settings().database_url)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        stmt = (
            select(InseminationORM, AnimalORM.tag, AnimalORM.name)
            .join(AnimalORM, AnimalORM.id == InseminationORM.animal_id)
            .where(InseminationORM.pregnancy_status == PregnancyStatus.PENDING.value)
            .where(InseminationORM.deleted_at.is_(None))
            .order_by(AnimalORM.tag, InseminationORM.service_date.desc())
        )
        if tenant_id:
            stmt = stmt.where(InseminationORM.tenant_id == tenant_id)
        rows = (await session.execute(stmt)).all()

        changed = 0
        for insemination, tag, name in rows:
            # Latest calving registered after this service, if any.
            calving_stmt = (
                select(AnimalEventORM)
                .where(AnimalEventORM.tenant_id == insemination.tenant_id)
                .where(AnimalEventORM.animal_id == insemination.animal_id)
                .where(AnimalEventORM.type == "CALVING")
                .where(AnimalEventORM.occurred_at > insemination.service_date)
                .order_by(AnimalEventORM.occurred_at)
                .limit(1)
            )
            calving = (await session.execute(calving_stmt)).scalar_one_or_none()
            if not calving:
                continue

            gestation_days = (calving.occurred_at.date() - insemination.service_date.date()).days
            fits_gestation = MIN_GESTATION_DAYS <= gestation_days <= MAX_GESTATION_DAYS

            # Only credit this service if no other service already claims the calving.
            if fits_gestation:
                taken_stmt = (
                    select(InseminationORM.id)
                    .where(InseminationORM.tenant_id == insemination.tenant_id)
                    .where(InseminationORM.calving_event_id == calving.id)
                    .limit(1)
                )
                if (await session.execute(taken_stmt)).scalar_one_or_none():
                    fits_gestation = False

            label = f"#{tag}" + (f" {name}" if name else "")
            if fits_gestation:
                action = "CONFIRMED (produced the calving)"
                insemination.pregnancy_status = PregnancyStatus.CONFIRMED.value
                insemination.expected_calving_date = calving.occurred_at.date()
                insemination.calving_event_id = calving.id
            else:
                action = f"OPEN (service {gestation_days}d before calving, did not take)"
                insemination.pregnancy_status = PregnancyStatus.OPEN.value
                insemination.expected_calving_date = None
            insemination.pregnancy_check_date = calving.occurred_at
            insemination.version += 1

            changed += 1
            print(
                f"{label}: service {insemination.service_date.date()} "
                f"-> calving {calving.occurred_at.date()} => {action}"
            )

        if dry_run:
            print(f"\n[dry-run] {changed} insemination(s) would be updated. Nothing written.")
        else:
            await session.commit()
            print(f"\n{changed} insemination(s) updated.")

    await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant-id", type=UUID, default=None, help="Limit to one tenant")
    parser.add_argument(
        "--dry-run", action="store_true", help="Report what would change without writing"
    )
    args = parser.parse_args()
    asyncio.run(resolve(args.tenant_id, args.dry_run))


if __name__ == "__main__":
    main()
