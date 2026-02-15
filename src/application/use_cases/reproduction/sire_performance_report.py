from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.errors import NotFound
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.sire_catalog import SireCatalog


@dataclass(slots=True)
class SirePerformanceOutput:
    sire: SireCatalog
    total_inseminations: int
    confirmed_pregnancies: int
    conception_rate: float  # 0.0 - 1.0


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    sire_id: UUID,
) -> SirePerformanceOutput:
    sire = await uow.sire_catalog.get(tenant_id, sire_id)
    if not sire:
        raise NotFound(f"Sire {sire_id} not found")

    total = await uow.inseminations.count_by_sire(tenant_id, sire_id)
    confirmed = await uow.inseminations.count_confirmed_by_sire(tenant_id, sire_id)
    rate = confirmed / total if total > 0 else 0.0

    return SirePerformanceOutput(
        sire=sire,
        total_inseminations=total,
        confirmed_pregnancies=confirmed,
        conception_rate=rate,
    )
