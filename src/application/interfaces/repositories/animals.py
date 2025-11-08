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
        limit: int | None = None,
        cursor: UUID | None = None,
        offset: int | None = None,
        is_active: bool | None = None,
        status_ids: list[UUID] | None = None,
        sort_by: str | None = None,
        sort_dir: str | None = None,
        search: str | None = None,
    ) -> list[Animal] | tuple[list[Animal], UUID | None]: ...

    async def count(
        self,
        tenant_id: UUID,
        *,
        is_active: bool | None = None,
        status_ids: list[UUID] | None = None,
        search: str | None = None,
    ) -> int: ...

    async def update(
        self,
        tenant_id: UUID,
        animal_id: UUID,
        data: dict,
        expected_version: int,
    ) -> Animal | None: ...

    async def delete(self, tenant_id: UUID, animal_id: UUID) -> bool: ...

    async def count_by_breed_id_or_name(
        self, tenant_id: UUID, *, breed_id: UUID | None = None, breed_name: str | None = None
    ) -> int: ...

    async def count_by_current_lot_id_or_name(
        self, tenant_id: UUID, *, lot_id: UUID | None = None, lot_name: str | None = None
    ) -> int: ...
