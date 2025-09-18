from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from src.application.errors import PermissionDenied
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.animal import Animal, AnimalStatus
from src.domain.value_objects.role import Role


@dataclass(slots=True)
class CreateAnimalInput:
    tag: str
    name: str | None = None
    breed: str | None = None
    birth_date: date | None = None
    lot: str | None = None
    status: AnimalStatus = AnimalStatus.ACTIVE
    photo_url: str | None = None


def ensure_can_create(role: Role) -> None:
    if not role.can_create():
        raise PermissionDenied("Role not allowed to create animals")


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    role: Role,
    payload: CreateAnimalInput,
) -> Animal:
    ensure_can_create(role)
    animal = Animal.create(
        tenant_id=tenant_id,
        tag=payload.tag,
        name=payload.name,
        breed=payload.breed,
        birth_date=payload.birth_date,
        lot=payload.lot,
        status=payload.status,
        photo_url=payload.photo_url,
    )
    created = await uow.animals.add(animal)
    await uow.commit()
    return created
