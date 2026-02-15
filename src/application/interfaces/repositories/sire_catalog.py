from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.models.sire_catalog import SireCatalog


class SireCatalogRepository(Protocol):
    async def add(self, sire: SireCatalog) -> SireCatalog: ...

    async def update(self, sire: SireCatalog) -> SireCatalog: ...

    async def get(self, tenant_id: UUID, sire_id: UUID) -> SireCatalog | None: ...

    async def list(
        self,
        tenant_id: UUID,
        active_only: bool = True,
        search: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[SireCatalog]: ...

    async def count(
        self,
        tenant_id: UUID,
        active_only: bool = True,
        search: str | None = None,
    ) -> int: ...

    async def delete(self, sire: SireCatalog) -> None: ...
