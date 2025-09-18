from __future__ import annotations

from uuid import UUID

from src.application.errors import NotFound
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.animal import Animal


async def execute(uow: UnitOfWork, tenant_id: UUID, animal_id: UUID) -> Animal:
    animal = await uow.animals.get(tenant_id, animal_id)
    if not animal:
        raise NotFound("Animal not found")
    return animal
