from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.models.animal_event import AnimalEvent


class AnimalEventsRepository(Protocol):
    async def add(self, event: AnimalEvent) -> AnimalEvent: ...

    async def get(self, tenant_id: UUID, event_id: UUID) -> AnimalEvent | None: ...

    async def list_by_animal(self, tenant_id: UUID, animal_id: UUID) -> list[AnimalEvent]: ...

    async def list_by_animal_paginated(
        self, tenant_id: UUID, animal_id: UUID, offset: int, limit: int
    ) -> list[AnimalEvent]: ...

    async def count_by_animal(self, tenant_id: UUID, animal_id: UUID) -> int: ...

    async def last_of_type(
        self, tenant_id: UUID, animal_id: UUID, event_type: str
    ) -> AnimalEvent | None: ...
