from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.models.animal_event import AnimalEvent


class AnimalEventsRepository(Protocol):
    async def add(self, event: AnimalEvent) -> AnimalEvent: ...

    async def get(self, tenant_id: UUID, event_id: UUID) -> AnimalEvent | None: ...

    async def list_by_animal(self, tenant_id: UUID, animal_id: UUID) -> list[AnimalEvent]: ...

    async def last_of_type(
        self, tenant_id: UUID, animal_id: UUID, event_type: str
    ) -> AnimalEvent | None: ...
