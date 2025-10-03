from __future__ import annotations

from datetime import datetime
from uuid import UUID

from src.application.interfaces.unit_of_work import UnitOfWork


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    animal_id: UUID,
    production_date_time: datetime,
) -> UUID | None:
    """Auto-link a milk production to an open lactation.

    Returns the lactation_id if a matching lactation was found, None otherwise.
    """

    # Find lactation that includes this date
    lactation = await uow.lactations.find_by_date(
        tenant_id=tenant_id,
        animal_id=animal_id,
        target_date=production_date_time.date(),
    )

    return lactation.id if lactation else None
