from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.health_record import HealthRecord


@dataclass
class ListHealthRecordsOutput:
    items: list[HealthRecord]
    total: int


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    animal_id: UUID,
    limit: int = 50,
    offset: int = 0,
) -> ListHealthRecordsOutput:
    """List health records for an animal."""

    items = await uow.health_records.list_by_animal(tenant_id, animal_id, limit, offset)
    total = await uow.health_records.count_by_animal(tenant_id, animal_id)

    return ListHealthRecordsOutput(items=items, total=total)
