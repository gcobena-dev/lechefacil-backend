from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from src.application.errors import PermissionDenied
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.animal import Animal
from src.domain.value_objects.role import Role


@dataclass(slots=True)
class CreateAnimalInput:
    tag: str
    name: str | None = None
    breed: str | None = None
    breed_variant: str | None = None
    breed_id: UUID | None = None
    birth_date: date | None = None
    lot: str | None = None
    current_lot_id: UUID | None = None
    status_id: UUID | None = None
    photo_url: str | None = None
    # Genealogy fields
    sex: str | None = None
    dam_id: UUID | None = None
    sire_id: UUID | None = None
    external_sire_code: str | None = None
    external_sire_registry: str | None = None


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
        breed_variant=payload.breed_variant,
        breed_id=payload.breed_id,
        birth_date=payload.birth_date,
        lot=payload.lot,
        current_lot_id=payload.current_lot_id,
        status_id=payload.status_id,
        photo_url=payload.photo_url,
        # Genealogy fields
        sex=payload.sex,
        dam_id=payload.dam_id,
        sire_id=payload.sire_id,
        external_sire_code=payload.external_sire_code,
        external_sire_registry=payload.external_sire_registry,
    )
    created = await uow.animals.add(animal)
    await uow.commit()
    return created
