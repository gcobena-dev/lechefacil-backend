from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.models.semen_inventory import SemenInventory


class SemenInventoryRepository(Protocol):
    async def add(self, stock: SemenInventory) -> SemenInventory: ...

    async def update(self, stock: SemenInventory) -> SemenInventory: ...

    async def get(self, tenant_id: UUID, stock_id: UUID) -> SemenInventory | None: ...

    async def list_by_sire(
        self,
        tenant_id: UUID,
        sire_catalog_id: UUID,
        in_stock_only: bool = False,
    ) -> list[SemenInventory]: ...

    async def list(
        self,
        tenant_id: UUID,
        in_stock_only: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[SemenInventory]: ...

    async def count(
        self,
        tenant_id: UUID,
        in_stock_only: bool = False,
    ) -> int: ...

    async def count_distinct_breeds(
        self,
        tenant_id: UUID,
        in_stock_only: bool = True,
    ) -> int: ...

    async def aggregate_stock_by_sire(
        self,
        tenant_id: UUID,
    ) -> dict[UUID, int]: ...

    async def get_autocomplete_values(
        self, tenant_id: UUID, limit: int = 50
    ) -> dict[str, list[str]]: ...

    async def delete(self, stock: SemenInventory) -> None: ...
