from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.errors import ValidationError
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.animal import Animal
from src.domain.models.animal_status import INACTIVE_STATUS_CODES


@dataclass(slots=True)
class AnimalsSummaryData:
    """Herd composition counters, computed ignoring the status filter."""

    production: int
    withdrawn: int
    other: int
    total: int


@dataclass(slots=True)
class ListAnimalsResult:
    items: list[Animal]
    next_cursor: UUID | None
    total: int | None = None
    summary: AnimalsSummaryData | None = None


async def _resolve_names(entities, ids: list[UUID]) -> list[str]:
    """Map a list of ids to their names using the given entity list."""
    by_id = {e.id: e.name for e in entities}
    return [by_id[i] for i in ids if i in by_id]


async def _compute_summary(
    uow: UnitOfWork,
    tenant_id: UUID,
    *,
    search: str | None,
    filter_kwargs: dict,
) -> AnimalsSummaryData:
    """Counters for the summary cards: the herd composition.

    Deliberately ignores the status filter (every other filter still applies),
    so the cards keep showing the whole breakdown and can be used to jump into
    a status: filtering by LACTATING must not zero out the "dados de baja" card.
    """

    async def code_id(code: str) -> UUID | None:
        status = await uow.animal_statuses.get_by_code(tenant_id, code)
        return status.id if status else None

    lactating_id = await code_id("LACTATING")
    inactive_ids = [i for i in [await code_id(c) for c in sorted(INACTIVE_STATUS_CODES)] if i]

    async def count_for(ids: list[UUID] | None) -> int:
        return await uow.animals.count(tenant_id, status_ids=ids, search=search, **filter_kwargs)

    total_count = await count_for(None)
    production = await count_for([lactating_id]) if lactating_id else 0
    withdrawn = await count_for(inactive_ids) if inactive_ids else 0
    other = max(total_count - production - withdrawn, 0)
    return AnimalsSummaryData(
        production=production,
        withdrawn=withdrawn,
        other=other,
        total=total_count,
    )


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
    breed_ids: list[UUID] | None = None,
    lot_ids: list[UUID] | None = None,
    sexes: list[str] | None = None,
    labels: list[str] | None = None,
    in_milk_withdrawal: bool | None = None,
    include_summary: bool = False,
) -> ListAnimalsResult:
    if limit <= 0 or limit > 500:
        raise ValidationError("limit must be between 1 and 500")

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
            empty_summary = AnimalsSummaryData(0, 0, 0, 0) if include_summary else None
            return ListAnimalsResult(items=[], next_cursor=None, total=0, summary=empty_summary)

    # Resolve breed / lot ids to their names so the repo can also match
    # legacy animals that only have the free-text name populated.
    breed_names = None
    if breed_ids:
        breed_names = await _resolve_names(await uow.breeds.list_for_tenant(tenant_id), breed_ids)
    lot_names = None
    if lot_ids:
        lot_names = await _resolve_names(await uow.lots.list_for_tenant(tenant_id), lot_ids)

    filter_kwargs = dict(
        breed_ids=breed_ids,
        breed_names=breed_names,
        lot_ids=lot_ids,
        lot_names=lot_names,
        sexes=sexes,
        labels=labels,
        in_milk_withdrawal=in_milk_withdrawal,
    )

    items, next_cursor = await uow.animals.list(
        tenant_id,
        limit=limit,
        cursor=cursor,
        offset=offset,
        status_ids=status_ids,
        sort_by=sort_by,
        sort_dir=sort_dir,
        search=search,
        **filter_kwargs,
    )

    # Get total count when using offset pagination
    total = None
    if offset is not None:
        total = await uow.animals.count(
            tenant_id, status_ids=status_ids, search=search, **filter_kwargs
        )

    summary = None
    if include_summary:
        summary = await _compute_summary(
            uow,
            tenant_id,
            search=search,
            filter_kwargs=filter_kwargs,
        )

    return ListAnimalsResult(items=items, next_cursor=next_cursor, total=total, summary=summary)
