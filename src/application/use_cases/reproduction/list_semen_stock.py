from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.semen_inventory import SemenInventory


@dataclass(slots=True)
class ListSemenStockOutput:
    items: list[SemenInventory]
    total: int


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    sire_catalog_id: UUID | None = None,
    in_stock_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> ListSemenStockOutput:
    if sire_catalog_id:
        items = await uow.semen_inventory.list_by_sire(
            tenant_id, sire_catalog_id, in_stock_only=in_stock_only
        )
        total = len(items)
    else:
        items = await uow.semen_inventory.list(
            tenant_id, in_stock_only=in_stock_only, limit=limit, offset=offset
        )
        total = await uow.semen_inventory.count(tenant_id, in_stock_only=in_stock_only)
    return ListSemenStockOutput(items=items, total=total)
