from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.insemination import Insemination


@dataclass(slots=True)
class ListInseminationsOutput:
    items: list[Insemination]
    total: int


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    animal_id: UUID | None = None,
    sire_catalog_id: UUID | None = None,
    pregnancy_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str | None = None,
    sort_dir: str | None = None,
) -> ListInseminationsOutput:
    items = await uow.inseminations.list(
        tenant_id,
        animal_id=animal_id,
        sire_catalog_id=sire_catalog_id,
        pregnancy_status=pregnancy_status,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )
    total = await uow.inseminations.count(
        tenant_id,
        animal_id=animal_id,
        sire_catalog_id=sire_catalog_id,
        pregnancy_status=pregnancy_status,
        date_from=date_from,
        date_to=date_to,
    )
    return ListInseminationsOutput(items=items, total=total)
