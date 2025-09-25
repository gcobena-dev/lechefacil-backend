from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass(slots=True)
class MilkPrice:
    id: UUID
    tenant_id: UUID
    date: date
    price_per_l: Decimal
    currency: str = "USD"
    buyer_id: UUID | None = None
    deleted_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        date: date,
        price_per_l: Decimal,
        currency: str = "USD",
        buyer_id: UUID | None = None,
    ) -> MilkPrice:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            date=date,
            price_per_l=price_per_l,
            currency=currency,
            buyer_id=buyer_id,
            created_at=now,
            updated_at=now,
            version=1,
        )
