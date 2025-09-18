from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.models.animal import Animal


class AnimalRepository(Protocol):
    async def add(self, animal: Animal) -> Animal: ...

    async def get(self, tenant_id: UUID, animal_id: UUID) -> Animal | None: ...

    async def list(
        self,
        tenant_id: UUID,
        *,
        limit: int,
        cursor: UUID | None,
    ) -> tuple[list[Animal], UUID | None]: ...

    async def update(
        self,
        tenant_id: UUID,
        animal_id: UUID,
        data: dict,
        expected_version: int,
    ) -> Animal | None: ...

    async def delete(self, tenant_id: UUID, animal_id: UUID) -> bool: ...
