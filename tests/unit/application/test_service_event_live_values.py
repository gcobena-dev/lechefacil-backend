"""The animal timeline must read services from `inseminations`, not from a copy.

A service used to be written twice: once in `inseminations` and once, flattened,
into the SERVICE event's `data`. Editing it in /reproduction only updated the
first, so the animal's Eventos tab kept showing the technician the service was
created with. The event now stores nothing about the service and the timeline
joins the live record on every read.
"""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.application.use_cases.animals.list_events import _attach_service_details
from src.domain.models.animal_event import AnimalEventType

TENANT_ID = uuid4()
ANIMAL_ID = uuid4()
SERVICE_AT = datetime(2026, 7, 8, 9, 0, tzinfo=timezone.utc)


def make_event(data: dict | None = None, occurred_at: datetime = SERVICE_AT):
    return SimpleNamespace(
        id=uuid4(),
        type=AnimalEventType.SERVICE.value,
        occurred_at=occurred_at,
        data=data,
    )


def make_insemination(*, service_event_id=None, technician=None, sire_catalog_id=None):
    return SimpleNamespace(
        id=uuid4(),
        service_event_id=service_event_id,
        service_date=SERVICE_AT,
        method="AI",
        technician=technician,
        sire_catalog_id=sire_catalog_id,
    )


class StubInseminations:
    def __init__(self, records: list):
        self._records = records

    async def get_by_service_event_ids(self, tenant_id, event_ids):
        return {
            r.service_event_id: r for r in self._records if r.service_event_id in set(event_ids)
        }

    async def list(self, tenant_id, animal_id=None):
        return list(self._records)


class StubSireCatalog:
    def __init__(self, sires: dict):
        self._sires = sires
        self.calls = 0

    async def get(self, tenant_id, sire_id):
        self.calls += 1
        return self._sires.get(sire_id)


def make_uow(records: list, sires: dict | None = None):
    return SimpleNamespace(
        inseminations=StubInseminations(records),
        sire_catalog=StubSireCatalog(sires or {}),
    )


@pytest.mark.asyncio
async def test_technician_comes_from_the_insemination_not_from_the_event():
    # The reported case: created as "Miguel Moreira", later edited to "Joel
    # Menéndez". The event still carries the original, and must not win.
    event = make_event({"technician": "Miguel Moreira", "method": "AI"})
    record = make_insemination(service_event_id=event.id, technician="Joel Menéndez")

    await _attach_service_details(make_uow([record]), TENANT_ID, ANIMAL_ID, [event])

    assert event.data["technician"] == "Joel Menéndez"
    assert event.data["insemination_id"] == str(record.id)


@pytest.mark.asyncio
async def test_clearing_the_technician_clears_it_on_the_timeline():
    event = make_event({"technician": "Miguel Moreira"})
    record = make_insemination(service_event_id=event.id, technician=None)

    await _attach_service_details(make_uow([record]), TENANT_ID, ANIMAL_ID, [event])

    assert event.data["technician"] is None


@pytest.mark.asyncio
async def test_sire_is_resolved_from_the_catalog_and_a_changed_bull_replaces_the_old():
    event = make_event({"sire_name": "TROVÃO 2B", "sire_code": "001GL00054"})
    new_sire_id = uuid4()
    record = make_insemination(service_event_id=event.id, sire_catalog_id=new_sire_id)
    sire = SimpleNamespace(
        id=new_sire_id, name="OLYMPIC", short_code="7HO14567", registry_code=None
    )

    await _attach_service_details(
        make_uow([record], {new_sire_id: sire}), TENANT_ID, ANIMAL_ID, [event]
    )

    assert event.data["sire_name"] == "OLYMPIC"
    assert event.data["sire_code"] == "7HO14567"
    assert event.data["sire_catalog_id"] == str(new_sire_id)


@pytest.mark.asyncio
async def test_a_bull_removed_from_the_service_disappears_from_the_timeline():
    event = make_event({"sire_name": "TROVÃO 2B", "sire_catalog_id": str(uuid4())})
    record = make_insemination(service_event_id=event.id, sire_catalog_id=None)

    await _attach_service_details(make_uow([record]), TENANT_ID, ANIMAL_ID, [event])

    assert "sire_name" not in event.data
    assert "sire_catalog_id" not in event.data


@pytest.mark.asyncio
async def test_events_predating_the_link_are_matched_by_day():
    event = make_event({"technician": "Miguel Moreira"})
    record = make_insemination(service_event_id=None, technician="Joel Menéndez")

    await _attach_service_details(make_uow([record]), TENANT_ID, ANIMAL_ID, [event])

    assert event.data["technician"] == "Joel Menéndez"


@pytest.mark.asyncio
async def test_an_event_with_no_insemination_keeps_its_own_data():
    # Imported herds and events registered before the reproduction module have
    # no record behind them: there, `data` is the service, not a copy of one.
    event = make_event(
        {"technician": "Miguel Moreira"}, occurred_at=datetime(2020, 1, 1, tzinfo=timezone.utc)
    )

    await _attach_service_details(make_uow([]), TENANT_ID, ANIMAL_ID, [event])

    assert event.data["technician"] == "Miguel Moreira"


@pytest.mark.asyncio
async def test_the_same_bull_on_several_events_is_fetched_once():
    sire_id = uuid4()
    events = [make_event({}), make_event({})]
    records = [make_insemination(service_event_id=e.id, sire_catalog_id=sire_id) for e in events]
    sire = SimpleNamespace(id=sire_id, name="OLYMPIC", short_code="7HO14567", registry_code=None)
    uow = make_uow(records, {sire_id: sire})

    await _attach_service_details(uow, TENANT_ID, ANIMAL_ID, events)

    assert uow.sire_catalog.calls == 1


@pytest.mark.asyncio
async def test_no_service_events_touches_no_repository():
    uow = SimpleNamespace()  # any attribute access would raise
    event = SimpleNamespace(id=uuid4(), type="CALVING", occurred_at=SERVICE_AT, data=None)

    await _attach_service_details(uow, TENANT_ID, ANIMAL_ID, [event])

    assert event.data is None


@pytest.mark.asyncio
async def test_an_unlinked_event_does_not_borrow_another_events_service():
    # Two services the same day: the linked one belongs to its own event, and
    # the unlinked event must not show it a second time.
    linked_event = make_event({})
    orphan_event = make_event({"technician": "Registrado a mano"})
    linked = make_insemination(service_event_id=linked_event.id, technician="Joel Menéndez")

    await _attach_service_details(
        make_uow([linked]), TENANT_ID, ANIMAL_ID, [linked_event, orphan_event]
    )

    assert linked_event.data["technician"] == "Joel Menéndez"
    assert orphan_event.data["technician"] == "Registrado a mano"
