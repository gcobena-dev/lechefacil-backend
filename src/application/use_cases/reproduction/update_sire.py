from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.errors import NotFound
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.sire_catalog import SireCatalog


@dataclass(slots=True)
class UpdateSireInput:
    sire_id: UUID
    name: str | None = None
    short_code: str | None = None
    registry_code: str | None = None
    registry_name: str | None = None
    breed_id: UUID | None = None
    animal_id: UUID | None = None
    is_active: bool | None = None
    genetic_notes: str | None = None
    data: dict | None = None


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    payload: UpdateSireInput,
) -> SireCatalog:
    sire = await uow.sire_catalog.get(tenant_id, payload.sire_id)
    if not sire:
        raise NotFound(f"Sire {payload.sire_id} not found")

    if payload.name is not None:
        sire.name = payload.name
    if payload.short_code is not None:
        sire.short_code = payload.short_code
    if payload.registry_code is not None:
        sire.registry_code = payload.registry_code
    if payload.registry_name is not None:
        sire.registry_name = payload.registry_name
    if payload.breed_id is not None:
        sire.breed_id = payload.breed_id
    if payload.animal_id is not None:
        sire.animal_id = payload.animal_id
    if payload.is_active is not None:
        sire.is_active = payload.is_active
    if payload.genetic_notes is not None:
        sire.genetic_notes = payload.genetic_notes
    if payload.data is not None:
        sire.data = payload.data

    sire.bump_version()
    return await uow.sire_catalog.update(sire)
