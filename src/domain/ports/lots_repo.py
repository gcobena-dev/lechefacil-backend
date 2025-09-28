from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.lot import Lot


class LotsRepo(ABC):
    @abstractmethod
    async def add(self, lot: Lot) -> Lot: ...

    @abstractmethod
    async def get(self, tenant_id: UUID, lot_id: UUID) -> Lot | None: ...

    @abstractmethod
    async def find_by_name(self, tenant_id: UUID, name: str) -> Lot | None: ...

    @abstractmethod
    async def list_for_tenant(
        self, tenant_id: UUID, *, active: bool | None = None
    ) -> list[Lot]: ...

    @abstractmethod
    async def update(self, tenant_id: UUID, lot_id: UUID, data: dict) -> Lot | None: ...

    @abstractmethod
    async def soft_delete(self, tenant_id: UUID, lot_id: UUID) -> bool: ...
