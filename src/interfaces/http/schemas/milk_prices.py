from __future__ import annotations

from datetime import date as DtDate
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MilkPriceCreate(BaseModel):
    date: DtDate
    price_per_l: Decimal
    currency: str = "USD"
    buyer_id: UUID | None = None


class MilkPriceUpdate(BaseModel):
    date: DtDate | None = None
    price_per_l: Decimal | None = None
    currency: str | None = None
    buyer_id: UUID | None = None


class MilkPriceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    date: DtDate
    price_per_l: Decimal
    currency: str
    buyer_id: UUID | None
    created_at: datetime
    updated_at: datetime
