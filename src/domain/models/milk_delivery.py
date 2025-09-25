from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass(slots=True)
class MilkDelivery:
    id: UUID
    tenant_id: UUID
    buyer_id: UUID
    date_time: datetime
    date: date
    volume_l: Decimal
    price_snapshot: Decimal
    currency: str
    amount: Decimal
    notes: str | None = None
    deleted_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        buyer_id: UUID,
        date_time: datetime,
        volume_l: Decimal,
        price_snapshot: Decimal,
        currency: str,
        amount: Decimal,
        notes: str | None = None,
    ) -> MilkDelivery:
        if date_time.tzinfo is None:
            date_time = date_time.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            buyer_id=buyer_id,
            date_time=date_time,
            date=date_time.date(),
            volume_l=volume_l,
            price_snapshot=price_snapshot,
            currency=currency,
            amount=amount,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )
