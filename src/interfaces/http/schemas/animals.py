from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.domain.models.animal import AnimalStatus


class AnimalBase(BaseModel):
    tag: str
    name: str | None = None
    breed: str | None = None
    birth_date: date | None = None
    lot: str | None = None
    status: AnimalStatus = AnimalStatus.ACTIVE
    photo_url: str | None = None


class AnimalCreate(AnimalBase):
    pass


class AnimalUpdate(BaseModel):
    version: int
    name: str | None = None
    breed: str | None = None
    birth_date: date | None = None
    lot: str | None = None
    status: AnimalStatus | None = None
    photo_url: str | None = None


class AnimalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    tag: str
    name: str | None
    breed: str | None
    birth_date: date | None
    lot: str | None
    status: AnimalStatus
    photo_url: str | None
    created_at: datetime
    updated_at: datetime
    version: int
    # Derived fields for attachments (optional in responses)
    primary_photo_url: str | None = None
    photos_count: int | None = None


class AnimalsListResponse(BaseModel):
    items: list[AnimalResponse]
    next_cursor: str | None = None


class AnimalValueResponse(BaseModel):
    animal_id: UUID
    date: date
    total_volume_l: Decimal
    price_per_l: Decimal
    currency: str
    amount: Decimal
    source: str  # deliveries_average | price_daily | tenant_default
