from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.sire_catalog import SireCatalog


@dataclass(slots=True)
class CreateSireInput:
    name: str
    short_code: str | None = None
    registry_code: str | None = None
    registry_name: str | None = None
    breed_id: UUID | None = None
    animal_id: UUID | None = None
    genetic_notes: str | None = None
    data: dict | None = None


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    payload: CreateSireInput,
) -> SireCatalog:
    sire = SireCatalog.create(
        tenant_id=tenant_id,
        name=payload.name,
        short_code=payload.short_code,
        registry_code=payload.registry_code,
        registry_name=payload.registry_name,
        breed_id=payload.breed_id,
        animal_id=payload.animal_id,
        genetic_notes=payload.genetic_notes,
        data=payload.data,
    )
    return await uow.sire_catalog.add(sire)
