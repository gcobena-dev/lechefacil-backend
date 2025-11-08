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
    total: int | None = None


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    *,
    limit: int,
    cursor: UUID | None = None,
    offset: int | None = None,
    status_codes: list[str] | None = None,
    sort_by: str | None = None,
    sort_dir: str | None = None,
    search: str | None = None,
) -> ListAnimalsResult:
    if limit <= 0 or limit > 100:
        raise ValidationError("limit must be between 1 and 100")

    # Convert status codes to status IDs if provided
    status_ids = None
    if status_codes:
        status_ids = []
        for code in status_codes:
            status = await uow.animal_statuses.get_by_code(tenant_id, code)
            if status:
                status_ids.append(status.id)
        # If no valid statuses found, return empty result
        if not status_ids:
            return ListAnimalsResult(items=[], next_cursor=None, total=0)

    items, next_cursor = await uow.animals.list(
        tenant_id,
        limit=limit,
        cursor=cursor,
        offset=offset,
        status_ids=status_ids,
        sort_by=sort_by,
        sort_dir=sort_dir,
        search=search,
    )

    # Get total count when using offset pagination
    total = None
    if offset is not None:
        total = await uow.animals.count(tenant_id, status_ids=status_ids, search=search)

    return ListAnimalsResult(items=items, next_cursor=next_cursor, total=total)
