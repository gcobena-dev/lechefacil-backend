from __future__ import annotations

from datetime import date
from typing import Protocol
from uuid import UUID

from src.domain.models.milk_delivery import MilkDelivery


class MilkDeliveriesRepository(Protocol):
    async def add(self, md: MilkDelivery) -> MilkDelivery: ...
    async def get(self, tenant_id: UUID, delivery_id: UUID) -> MilkDelivery | None: ...
    async def list(
        self,
        tenant_id: UUID,
        *,
        date_from: date | None,
        date_to: date | None,
        buyer_id: UUID | None,
    ) -> list[MilkDelivery]: ...
    async def update(
        self, tenant_id: UUID, delivery_id: UUID, data: dict
    ) -> MilkDelivery | None: ...
    async def delete(self, tenant_id: UUID, delivery_id: UUID) -> bool: ...
    async def summarize(
        self,
        tenant_id: UUID,
        *,
        date_from: date,
        date_to: date,
        buyer_id: UUID | None,
        period: str,
    ) -> list[dict]: ...
