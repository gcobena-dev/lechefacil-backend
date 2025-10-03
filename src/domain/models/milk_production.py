from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass(slots=True)
class MilkProduction:
    id: UUID
    tenant_id: UUID
    animal_id: UUID | None
    buyer_id: UUID | None
    date_time: datetime
    date: date
    shift: str
    input_unit: str  # 'kg' | 'lb' | 'l'
    input_quantity: Decimal
    density: Decimal  # e.g., 1.03
    volume_l: Decimal
    lactation_id: UUID | None = None
    price_snapshot: Decimal | None = None
    currency: str = "USD"
    amount: Decimal | None = None
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
        animal_id: UUID | None,
        buyer_id: UUID | None,
        lactation_id: UUID | None = None,
        date_time: datetime,
        shift: str,
        input_unit: str,
        input_quantity: Decimal,
        density: Decimal,
        volume_l: Decimal,
        price_snapshot: Decimal | None = None,
        currency: str = "USD",
        amount: Decimal | None = None,
        notes: str | None = None,
    ) -> MilkProduction:
        if date_time.tzinfo is None:
            date_time = date_time.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            animal_id=animal_id,
            buyer_id=buyer_id,
            lactation_id=lactation_id,
            date_time=date_time,
            date=date_time.date(),
            shift=shift,
            input_unit=input_unit,
            input_quantity=input_quantity,
            density=density,
            volume_l=volume_l,
            price_snapshot=price_snapshot,
            currency=currency,
            amount=amount,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )
