from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from src.application.errors import ConflictError, PermissionDenied, ValidationError
from src.application.use_cases.animals import (
    create_animal,
    delete_animal,
    list_animals,
    update_animal,
)
from src.domain.models.animal import Animal
from src.domain.value_objects.role import Role


class StubRepo:
    def __init__(self) -> None:
        self.add_called = False
        self.add_input = None
        self.stored = None

    async def add(self, animal: Animal) -> Animal:
        self.add_called = True
        self.add_input = animal
        self.stored = animal
        return animal

    async def list(self, tenant_id, *, limit, cursor):
        return [], None

    async def get(self, tenant_id, animal_id):
        return Animal.create(tenant_id=tenant_id, tag="existing")

    async def update(self, tenant_id, animal_id, data, expected_version):
        return None

    async def delete(self, tenant_id, animal_id):
        return False


def make_uow(repo: StubRepo):
    async def commit():
        return None

    async def rollback():
        return None

    events: list = []

    def add_event(event):
        events.append(event)

    def drain_events():
        nonlocal events
        evts, events = events, []
        return evts

    return SimpleNamespace(
        animals=repo,
        commit=commit,
        rollback=rollback,
        add_event=add_event,
        drain_events=drain_events,
    )


@pytest.mark.asyncio
async def test_create_animal_denies_worker():
    repo = StubRepo()
    uow = make_uow(repo)
    with pytest.raises(PermissionDenied):
        await create_animal.execute(
            uow,
            uuid4(),
            Role.WORKER,
            uuid4(),
            create_animal.CreateAnimalInput(tag="TAG-1"),
        )
    assert not repo.add_called


@pytest.mark.asyncio
async def test_create_animal_with_manager_succeeds():
    repo = StubRepo()
    uow = make_uow(repo)
    result = await create_animal.execute(
        uow,
        uuid4(),
        Role.MANAGER,
        uuid4(),
        create_animal.CreateAnimalInput(tag="TAG-2", status_id=None),
    )
    assert repo.add_called
    assert result.tag == "TAG-2"


@pytest.mark.asyncio
async def test_list_animals_validates_limit():
    repo = StubRepo()
    uow = make_uow(repo)
    with pytest.raises(ValidationError):
        await list_animals.execute(uow, uuid4(), limit=0, cursor=None)


@pytest.mark.asyncio
async def test_update_conflict_raises():
    repo = StubRepo()

    async def update_stub(tenant_id, animal_id, data, expected_version):
        return None

    repo.update = update_stub  # type: ignore

    uow = make_uow(repo)
    with pytest.raises(ConflictError):
        await update_animal.execute(
            uow,
            uuid4(),
            Role.ADMIN,
            uuid4(),
            uuid4(),
            update_animal.UpdateAnimalInput(version=1, name="New"),
        )


@pytest.mark.asyncio
async def test_delete_requires_admin():
    repo = StubRepo()

    async def delete_stub(tenant_id, animal_id):
        return True

    repo.delete = delete_stub  # type: ignore

    uow = make_uow(repo)
    with pytest.raises(PermissionDenied):
        await delete_animal.execute(uow, uuid4(), Role.MANAGER, uuid4())

    await delete_animal.execute(uow, uuid4(), Role.ADMIN, uuid4())
