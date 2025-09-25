from __future__ import annotations

from datetime import date
from typing import Protocol
from uuid import UUID

from src.domain.models.milk_price import MilkPrice


class MilkPricesRepository(Protocol):
    async def add(self, price: MilkPrice) -> MilkPrice: ...
    async def update(self, tenant_id: UUID, price_id: UUID, data: dict) -> MilkPrice | None: ...
    async def delete(self, tenant_id: UUID, price_id: UUID) -> bool: ...
    async def list(
        self,
        tenant_id: UUID,
        *,
        date_from: date | None,
        date_to: date | None,
        buyer_id: UUID | None,
    ) -> list[MilkPrice]: ...
    async def get_for_date(
        self, tenant_id: UUID, the_date: date, buyer_id: UUID | None
    ) -> MilkPrice | None: ...
    async def get_existing(
        self, tenant_id: UUID, the_date: date, buyer_id: UUID | None
    ) -> MilkPrice | None: ...
    async def get_most_recent(self, tenant_id: UUID) -> MilkPrice | None: ...
