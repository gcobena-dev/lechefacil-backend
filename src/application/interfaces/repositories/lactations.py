from __future__ import annotations

from datetime import date
from typing import Protocol
from uuid import UUID

from src.domain.models.lactation import Lactation


class LactationsRepository(Protocol):
    async def add(self, lactation: Lactation) -> Lactation: ...

    async def get(self, tenant_id: UUID, lactation_id: UUID) -> Lactation | None: ...

    async def get_open(self, tenant_id: UUID, animal_id: UUID) -> Lactation | None: ...

    async def get_last_number(self, tenant_id: UUID, animal_id: UUID) -> int: ...

    async def list_by_animal(self, tenant_id: UUID, animal_id: UUID) -> list[Lactation]: ...

    async def update(self, lactation: Lactation) -> Lactation: ...

    async def sum_volume(self, lactation_id: UUID) -> float: ...

    async def find_by_date(
        self, tenant_id: UUID, animal_id: UUID, target_date: date
    ) -> Lactation | None:
        """Find a lactation that includes the given date."""
        ...
