from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.errors import NotFound
from src.application.interfaces.unit_of_work import UnitOfWork
from src.application.patching import resolve_patch
from src.domain.models.sire_catalog import SireCatalog

#: Columns that may be blanked out; `name` and `is_active` are NOT NULL.
CLEARABLE_FIELDS = frozenset(
    {
        "short_code",
        "registry_code",
        "registry_name",
        "breed_id",
        "animal_id",
        "genetic_notes",
        "data",
    }
)

PATCHABLE_FIELDS = ("name", "is_active", *sorted(CLEARABLE_FIELDS))


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
    #: Field names the client actually sent, so a `null` can clear a field
    #: instead of being read as "not provided".
    fields_set: frozenset[str] = frozenset()


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    payload: UpdateSireInput,
) -> SireCatalog:
    sire = await uow.sire_catalog.get(tenant_id, payload.sire_id)
    if not sire:
        raise NotFound(f"Sire {payload.sire_id} not found")

    for name, value in resolve_patch(
        payload,
        PATCHABLE_FIELDS,
        sent=payload.fields_set,
        nullable=CLEARABLE_FIELDS,
    ).items():
        setattr(sire, name, value)

    sire.bump_version()
    return await uow.sire_catalog.update(sire)
