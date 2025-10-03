from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.models.animal_parentage import AnimalParentage


class AnimalParentageRepository(Protocol):
    async def add(self, parentage: AnimalParentage) -> AnimalParentage: ...

    async def get_current(
        self, tenant_id: UUID, child_id: UUID, relation: str
    ) -> AnimalParentage | None:
        """Get the current/active parentage record for a child and relation."""
        ...

    async def list_by_child(self, tenant_id: UUID, child_id: UUID) -> list[AnimalParentage]: ...

    async def set_current(
        self,
        child_id: UUID,
        relation: str,
        parent_animal_id: UUID | None = None,
        external_code: str | None = None,
        external_registry: str | None = None,
    ) -> AnimalParentage:
        """Set or update the current parentage for a child.

        This is used to keep animals.dam_id/sire_id in sync.
        """
        ...
