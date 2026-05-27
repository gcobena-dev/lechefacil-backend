from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.sire_catalog import SireCatalog


@dataclass(slots=True)
class SirePerformanceSummaryItem:
    sire: SireCatalog
    total_inseminations: int
    confirmed_pregnancies: int
    conception_rate: float
    straws_used: int
    straws_in_stock: int


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    date_from: datetime,
    date_to: datetime,
    include_inactive: bool = False,
) -> list[SirePerformanceSummaryItem]:
    sires = await uow.sire_catalog.list(
        tenant_id,
        active_only=not include_inactive,
        limit=None,
    )
    insem_agg = await uow.inseminations.aggregate_by_sire(
        tenant_id, date_from, date_to
    )
    stock_agg = await uow.semen_inventory.aggregate_stock_by_sire(tenant_id)

    items: list[SirePerformanceSummaryItem] = []
    for sire in sires:
        agg = insem_agg.get(sire.id, {})
        total = int(agg.get("total_inseminations", 0))
        confirmed = int(agg.get("confirmed_pregnancies", 0))
        straws_used = int(agg.get("straws_used", 0))
        rate = (confirmed / total) if total > 0 else 0.0
        items.append(
            SirePerformanceSummaryItem(
                sire=sire,
                total_inseminations=total,
                confirmed_pregnancies=confirmed,
                conception_rate=rate,
                straws_used=straws_used,
                straws_in_stock=int(stock_agg.get(sire.id, 0)),
            )
        )
    return items
