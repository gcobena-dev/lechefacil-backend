from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.models.animal_status import AnimalStatus


class AnimalStatusesRepo(ABC):
    @abstractmethod
    async def add(self, status: AnimalStatus) -> AnimalStatus:
        pass

    @abstractmethod
    async def get_by_id(self, status_id: UUID) -> AnimalStatus | None:
        pass

    @abstractmethod
    async def get_by_code(self, tenant_id: UUID | None, code: str) -> AnimalStatus | None:
        pass

    @abstractmethod
    async def list_for_tenant(self, tenant_id: UUID) -> list[AnimalStatus]:
        pass
