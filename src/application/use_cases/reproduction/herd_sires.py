"""Bulls of the herd in the sire catalog.

A herd bull used for natural service is both an animal and a catalog sire; the
catalog entry points at the animal through `sire_catalog.animal_id`. These use
cases keep that link valid and let the farm bring its bulls into the catalog
without retyping them.
"""

from __future__ import annotations

from uuid import UUID

from src.application.errors import ValidationError
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.animal import Animal
from src.domain.models.sire_catalog import SireCatalog


async def ensure_herd_bull(
    uow: UnitOfWork,
    tenant_id: UUID,
    animal_id: UUID,
    *,
    sire_id: UUID | None = None,
) -> Animal:
    """The animal a catalog sire may point at: a male of this farm that is not
    already linked to another catalog entry (`sire_id` is the entry being
    edited, which may keep its own link)."""
    animal = await uow.animals.get(tenant_id, animal_id)
    if not animal:
        raise ValidationError("El animal seleccionado no existe en el hato")
    if animal.sex != "MALE":
        raise ValidationError("Solo un macho del hato puede ser un toro del catálogo")
    linked = await uow.sire_catalog.get_by_animal(tenant_id, animal_id)
    if linked and linked.id != sire_id:
        raise ValidationError(f"El animal {animal.tag} ya está en el catálogo como {linked.name}")
    return animal


async def list_herd_candidates(uow: UnitOfWork, tenant_id: UUID) -> list[Animal]:
    """Active males of the herd that are not in the catalog yet."""
    result = await uow.animals.list(tenant_id, is_active=True)
    animals = result[0] if isinstance(result, tuple) else result
    sires = await uow.sire_catalog.list(tenant_id, active_only=False)
    linked = {s.animal_id for s in sires if s.animal_id}
    males = [
        a for a in animals if a.sex == "MALE" and a.id not in linked and a.disposition_at is None
    ]
    return sorted(males, key=lambda a: a.tag)


async def import_from_herd(
    uow: UnitOfWork, tenant_id: UUID, animal_ids: list[UUID]
) -> list[SireCatalog]:
    """Create a catalog sire for each herd bull, named after the animal."""
    if not animal_ids:
        raise ValidationError("Selecciona al menos un toro del hato")
    created: list[SireCatalog] = []
    for animal_id in dict.fromkeys(animal_ids):
        animal = await ensure_herd_bull(uow, tenant_id, animal_id)
        sire = SireCatalog.create(
            tenant_id=tenant_id,
            name=animal.name or animal.tag,
            short_code=animal.tag,
            breed_id=animal.breed_id,
            animal_id=animal.id,
        )
        created.append(await uow.sire_catalog.add(sire))
    return created
