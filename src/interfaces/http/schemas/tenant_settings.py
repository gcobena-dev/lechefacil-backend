from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TenantBillingSettings(BaseModel):
    default_buyer_id: UUID | None = None
    default_density: Decimal = Decimal("1.03")
    default_delivery_input_unit: str = "l"
    default_production_input_unit: str = "lb"
    default_currency: str = "USD"
    default_price_per_l: Decimal | None = None


class TenantBillingResponse(TenantBillingSettings):
    model_config = ConfigDict(from_attributes=True)
    updated_at: datetime
