from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LactationBase(BaseModel):
    animal_id: UUID
    number: int
    start_date: date
    end_date: date | None = None
    status: str = "open"  # 'open' | 'closed'


class LactationCreate(BaseModel):
    animal_id: UUID
    start_date: date
    calving_event_id: UUID | None = None


class LactationUpdate(BaseModel):
    version: int
    end_date: date | None = None
    status: str | None = None


class LactationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    animal_id: UUID
    number: int
    start_date: date
    end_date: date | None
    status: str
    calving_event_id: UUID | None
    created_at: datetime
    updated_at: datetime
    version: int

    # Computed fields (optional, populated by use cases)
    total_volume_l: Decimal | None = None
    days_in_milk: int | None = None
    average_daily_l: Decimal | None = None
    production_count: int | None = None


class LactationsListResponse(BaseModel):
    items: list[LactationResponse]


class LactationMetrics(BaseModel):
    lactation_id: UUID
    total_volume_l: Decimal
    days_in_milk: int
    average_daily_l: Decimal
    peak_volume_l: Decimal | None = None
    peak_date: date | None = None
    production_count: int
