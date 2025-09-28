from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.breed import Breed


class BreedsRepo(ABC):
    @abstractmethod
    async def add(self, breed: Breed) -> Breed: ...

    @abstractmethod
    async def get(self, tenant_id: UUID, breed_id: UUID) -> Breed | None: ...

    @abstractmethod
    async def get_any(self, breed_id: UUID) -> Breed | None: ...

    @abstractmethod
    async def find_by_name(self, tenant_id: UUID, name: str) -> Breed | None: ...

    @abstractmethod
    async def list_for_tenant(
        self, tenant_id: UUID, *, active: bool | None = None
    ) -> list[Breed]: ...

    @abstractmethod
    async def update(self, tenant_id: UUID, breed_id: UUID, data: dict) -> Breed | None: ...

    @abstractmethod
    async def soft_delete(self, tenant_id: UUID, breed_id: UUID) -> bool: ...
