from __future__ import annotations

from datetime import date
from typing import Protocol
from uuid import UUID

from src.domain.models.milk_production import MilkProduction


class MilkProductionsRepository(Protocol):
    async def add(self, mp: MilkProduction) -> MilkProduction: ...
    async def get(self, tenant_id: UUID, production_id: UUID) -> MilkProduction | None: ...
    async def list(
        self,
        tenant_id: UUID,
        *,
        date_from: date | None,
        date_to: date | None,
        animal_id: UUID | None,
        order_by: str | None = None,  # 'recent' | 'volume' | 'name'
        order: str | None = None,  # 'asc' | 'desc'
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[MilkProduction]: ...
    async def count(
        self,
        tenant_id: UUID,
        *,
        date_from: date | None,
        date_to: date | None,
        animal_id: UUID | None,
    ) -> int: ...
    async def update(
        self, tenant_id: UUID, production_id: UUID, data: dict
    ) -> MilkProduction | None: ...
    async def delete(self, tenant_id: UUID, production_id: UUID) -> bool: ...
