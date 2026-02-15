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

    async def delete(self, stock: SemenInventory) -> None: ...
