from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.application.use_cases.animals.register_event import (
    _resolve_inseminations_on_calving,
)
from src.application.use_cases.reproduction.list_reproductive_animals import (
    _is_superseded_by_calving,
)
from src.domain.models.insemination import GESTATION_DAYS, Insemination, PregnancyStatus

TENANT_ID = uuid4()
ANIMAL_ID = uuid4()
CALVING_AT = datetime(2026, 6, 18, tzinfo=timezone.utc)


def make_insemination(days_before_calving: int) -> Insemination:
    return Insemination.create(
        tenant_id=TENANT_ID,
        animal_id=ANIMAL_ID,
        service_date=CALVING_AT - timedelta(days=days_before_calving),
        method="NATURAL",
    )


class StubInseminationsRepo:
    def __init__(self, pending: list[Insemination], confirmed: Insemination | None = None):
        self._pending = pending
        self._confirmed = confirmed
        self.updated: list[Insemination] = []

    async def get_latest_confirmed(self, tenant_id, animal_id):
        return self._confirmed

    async def list_pending_before(self, tenant_id, animal_id, before):
        return [i for i in self._pending if i.service_date <= before]

    async def update(self, insemination):
        self.updated.append(insemination)
        return insemination


def make_uow(repo: StubInseminationsRepo):
    return SimpleNamespace(inseminations=repo)


@pytest.mark.asyncio
async def test_pending_service_within_gestation_is_credited_with_the_calving():
    service = make_insemination(GESTATION_DAYS)
    repo = StubInseminationsRepo(pending=[service])
    event = SimpleNamespace(id=uuid4(), occurred_at=CALVING_AT)

    await _resolve_inseminations_on_calving(
        make_uow(repo), TENANT_ID, SimpleNamespace(id=ANIMAL_ID), event
    )

    assert service.pregnancy_status == PregnancyStatus.CONFIRMED.value
    assert service.calving_event_id == event.id
    assert repo.updated == [service]


@pytest.mark.asyncio
async def test_pending_service_too_close_to_the_calving_is_closed_as_open():
    # The reported case: a service 117 days before calving cannot have produced
    # it, so it must not keep the cow flagged as "Inseminada".
    service = make_insemination(117)
    repo = StubInseminationsRepo(pending=[service])
    event = SimpleNamespace(id=uuid4(), occurred_at=CALVING_AT)

    await _resolve_inseminations_on_calving(
        make_uow(repo), TENANT_ID, SimpleNamespace(id=ANIMAL_ID), event
    )

    assert service.pregnancy_status == PregnancyStatus.OPEN.value
    assert service.calving_event_id is None


@pytest.mark.asyncio
async def test_only_one_service_is_credited_and_earlier_ones_are_closed():
    winner = make_insemination(GESTATION_DAYS)
    earlier = make_insemination(GESTATION_DAYS + 60)
    repo = StubInseminationsRepo(pending=[winner, earlier])
    event = SimpleNamespace(id=uuid4(), occurred_at=CALVING_AT)

    await _resolve_inseminations_on_calving(
        make_uow(repo), TENANT_ID, SimpleNamespace(id=ANIMAL_ID), event
    )

    assert winner.pregnancy_status == PregnancyStatus.CONFIRMED.value
    assert earlier.pregnancy_status == PregnancyStatus.OPEN.value


@pytest.mark.asyncio
async def test_pending_service_is_closed_when_a_confirmed_one_already_claims_the_calving():
    confirmed = make_insemination(GESTATION_DAYS)
    confirmed.confirm_pregnancy(check_date=CALVING_AT - timedelta(days=240))
    pending = make_insemination(150)
    repo = StubInseminationsRepo(pending=[pending], confirmed=confirmed)
    event = SimpleNamespace(id=uuid4(), occurred_at=CALVING_AT)

    await _resolve_inseminations_on_calving(
        make_uow(repo), TENANT_ID, SimpleNamespace(id=ANIMAL_ID), event
    )

    assert confirmed.calving_event_id == event.id
    assert pending.pregnancy_status == PregnancyStatus.OPEN.value


def test_service_before_the_last_calving_is_superseded():
    ins = {"service_date": datetime(2026, 2, 21, tzinfo=timezone.utc)}
    assert _is_superseded_by_calving(ins, CALVING_AT.date()) is True


def test_service_after_the_last_calving_is_still_the_active_cycle():
    ins = {"service_date": datetime(2026, 7, 20, tzinfo=timezone.utc)}
    assert _is_superseded_by_calving(ins, CALVING_AT.date()) is False


def test_service_is_not_superseded_when_the_cow_never_calved():
    ins = {"service_date": datetime(2026, 2, 21, tzinfo=timezone.utc)}
    assert _is_superseded_by_calving(ins, None) is False
