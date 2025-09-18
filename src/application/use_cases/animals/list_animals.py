from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.errors import ValidationError
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.animal import Animal


@dataclass(slots=True)
class ListAnimalsResult:
    items: list[Animal]
    next_cursor: UUID | None


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    *,
    limit: int,
    cursor: UUID | None,
) -> ListAnimalsResult:
    if limit <= 0 or limit > 100:
        raise ValidationError("limit must be between 1 and 100")
    items, next_cursor = await uow.animals.list(tenant_id, limit=limit, cursor=cursor)
    return ListAnimalsResult(items=items, next_cursor=next_cursor)
