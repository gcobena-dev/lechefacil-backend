from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from src.application.errors import NotFound, PermissionDenied
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.animal_event import AnimalEvent, AnimalEventType
from src.domain.value_objects.role import Role

SERVICE_EVENT_TYPES = (AnimalEventType.SERVICE.value, AnimalEventType.EMBRYO_TRANSFER.value)


def ensure_can_view(role: Role) -> None:
    if not role.can_read():
        raise PermissionDenied("Role not allowed to view events")


@dataclass(slots=True)
class ListEventsResult:
    items: list[AnimalEvent]
    total: int
    page: int
    per_page: int


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    role: Role,
    animal_id: UUID,
    page: int = 1,
    per_page: int = 10,
) -> ListEventsResult:
    """List events for an animal with pagination."""

    ensure_can_view(role)

    # Verify animal exists
    animal = await uow.animals.get(tenant_id, animal_id)
    if not animal:
        raise NotFound(f"Animal {animal_id} not found")

    # Clamp pagination parameters
    page = max(1, page)
    per_page = max(1, per_page)

    total = await uow.animal_events.count_by_animal(tenant_id, animal_id)
    offset = (page - 1) * per_page
    items = await uow.animal_events.list_by_animal_paginated(tenant_id, animal_id, offset, per_page)

    await _attach_sire(uow, tenant_id, animal_id, items)

    return ListEventsResult(items=items, total=total, page=page, per_page=per_page)


async def _attach_sire(
    uow: UnitOfWork,
    tenant_id: UUID,
    animal_id: UUID,
    items: list[AnimalEvent],
) -> None:
    """Fill in the bull of SERVICE events so the timeline can link to his page.

    Events recorded from an insemination carry `sire_catalog_id`. Older ones
    only kept the free-text code, so they are matched back to the insemination
    registered for the same animal on the same day. The resolved name and code
    are added to the event data for display; nothing is written back to the DB.
    """
    service_events = [e for e in items if e.type in SERVICE_EVENT_TYPES]
    if not service_events:
        return

    inseminations_by_day: dict[date, UUID] | None = None
    sires: dict[UUID, object] = {}

    for event in service_events:
        data = dict(event.data or {})
        raw_id = data.get("sire_catalog_id")

        if raw_id is None:
            if inseminations_by_day is None:
                records = await uow.inseminations.list(tenant_id, animal_id=animal_id)
                inseminations_by_day = {
                    r.service_date.date(): r.sire_catalog_id
                    for r in records
                    if r.service_date and r.sire_catalog_id
                }
            raw_id = inseminations_by_day.get(event.occurred_at.date())

        if raw_id is None:
            continue

        try:
            sire_id = raw_id if isinstance(raw_id, UUID) else UUID(str(raw_id))
        except (ValueError, AttributeError):
            continue

        if sire_id not in sires:
            sires[sire_id] = await uow.sire_catalog.get(tenant_id, sire_id)
        sire = sires[sire_id]
        if sire is None:
            continue

        data["sire_catalog_id"] = str(sire.id)
        data["sire_name"] = sire.name
        data["sire_code"] = sire.short_code or sire.registry_code
        event.data = data
