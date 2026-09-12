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

    await _attach_service_details(uow, tenant_id, animal_id, items)

    return ListEventsResult(items=items, total=total, page=page, per_page=per_page)


async def _attach_service_details(
    uow: UnitOfWork,
    tenant_id: UUID,
    animal_id: UUID,
    items: list[AnimalEvent],
) -> None:
    """Fill SERVICE events with the live insemination behind them.

    A service is stored once, in `inseminations`; the SERVICE event only marks
    it on the timeline. The bull, the method and the technician are read from
    that record every time the timeline is served, so editing a service in
    /reproduction is reflected here immediately. Older events that still carry
    a copy of those values in `data` are overwritten by the live ones, which is
    what fixes the rows already saved with a stale technician.

    The link is `insemination.service_event_id`. Services created before that
    link existed are matched back by animal and day. Events with no insemination
    at all (imported, or registered straight on the timeline) keep whatever
    `data` holds — there it is the record, not a copy of one.

    Nothing is written back to the DB.
    """
    service_events = [e for e in items if e.type in SERVICE_EVENT_TYPES]
    if not service_events:
        return

    by_event = await uow.inseminations.get_by_service_event_ids(
        tenant_id, [e.id for e in service_events]
    )

    unlinked = [e for e in service_events if e.id not in by_event]
    by_day: dict[date, object] = {}
    if unlinked:
        # Records already claimed by an event id are left out, so an unlinked
        # event on the same day cannot borrow another event's service and show
        # it twice on the timeline.
        claimed = {r.id for r in by_event.values()}
        records = await uow.inseminations.list(tenant_id, animal_id=animal_id)
        for r in records:
            if r.service_date and r.id not in claimed:
                by_day.setdefault(r.service_date.date(), r)

    sires: dict[UUID, object] = {}

    for event in service_events:
        record = by_event.get(event.id) or by_day.get(event.occurred_at.date())
        if record is None:
            continue

        data = dict(event.data or {})
        data["insemination_id"] = str(record.id)
        data["method"] = record.method
        # Written even when empty so a technician cleared in /reproduction
        # disappears here too instead of falling back to the old copy.
        data["technician"] = record.technician
        data.pop("sire_name", None)
        data.pop("sire_code", None)
        data.pop("sire_catalog_id", None)
        data.pop("external_sire_code", None)
        data.pop("external_sire_registry", None)

        sire_id = record.sire_catalog_id
        if sire_id is not None:
            if sire_id not in sires:
                sires[sire_id] = await uow.sire_catalog.get(tenant_id, sire_id)
            sire = sires[sire_id]
            if sire is not None:
                data["sire_catalog_id"] = str(sire.id)
                data["sire_name"] = sire.name
                data["sire_code"] = sire.short_code or sire.registry_code

        event.data = data
