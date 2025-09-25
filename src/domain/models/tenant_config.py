from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID


@dataclass(slots=True)
class TenantConfig:
    tenant_id: UUID
    default_buyer_id: UUID | None = None
    default_density: Decimal = Decimal("1.03")
    default_delivery_input_unit: str = "l"
    default_production_input_unit: str = "lb"
    default_currency: str = "USD"
    default_price_per_l: Decimal | None = None
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
