from __future__ import annotations

from datetime import date as DtDate
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MilkDeliveryCreate(BaseModel):
    date_time: datetime
    volume_l: Decimal
    buyer_id: UUID | None = None
    notes: str | None = None


class MilkDeliveryUpdate(BaseModel):
    version: int
    date_time: datetime | None = None
    volume_l: Decimal | None = None
    buyer_id: UUID | None = None
    notes: str | None = None


class MilkDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    date: DtDate
    date_time: datetime
    volume_l: Decimal
    buyer_id: UUID
    price_snapshot: Decimal
    currency: str
    amount: Decimal
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class DeliverySummaryItem(BaseModel):
    period: str
    total_liters: Decimal
    total_amount: Decimal
