from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.sire_catalog import SireCatalog


@dataclass(slots=True)
class ListSiresOutput:
    items: list[SireCatalog]
    total: int


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    active_only: bool = True,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> ListSiresOutput:
    items = await uow.sire_catalog.list(
        tenant_id, active_only=active_only, search=search, limit=limit, offset=offset
    )
    total = await uow.sire_catalog.count(tenant_id, active_only=active_only, search=search)
    return ListSiresOutput(items=items, total=total)
