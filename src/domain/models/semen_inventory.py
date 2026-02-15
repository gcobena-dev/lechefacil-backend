from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4


@dataclass(slots=True)
class SemenInventory:
    id: UUID
    tenant_id: UUID
    sire_catalog_id: UUID
    initial_quantity: int
    current_quantity: int

    batch_code: str | None = None
    tank_id: str | None = None
    canister_position: str | None = None
    supplier: str | None = None
    cost_per_straw: Decimal | None = None
    currency: str = "USD"
    purchase_date: date | None = None
    expiry_date: date | None = None
    notes: str | None = None

    deleted_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        sire_catalog_id: UUID,
        initial_quantity: int,
        batch_code: str | None = None,
        tank_id: str | None = None,
        canister_position: str | None = None,
        supplier: str | None = None,
        cost_per_straw: Decimal | None = None,
        currency: str = "USD",
        purchase_date: date | None = None,
        expiry_date: date | None = None,
        notes: str | None = None,
    ) -> SemenInventory:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            sire_catalog_id=sire_catalog_id,
            initial_quantity=initial_quantity,
            current_quantity=initial_quantity,
            batch_code=batch_code,
            tank_id=tank_id,
            canister_position=canister_position,
            supplier=supplier,
            cost_per_straw=cost_per_straw,
            currency=currency,
            purchase_date=purchase_date,
            expiry_date=expiry_date,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )

    def use_straws(self, count: int = 1) -> None:
        if count > self.current_quantity:
            raise ValueError(
                f"Not enough straws: requested {count}, available {self.current_quantity}"
            )
        self.current_quantity -= count
        self.bump_version()

    def bump_version(self) -> None:
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)
