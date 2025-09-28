from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AnimalBase(BaseModel):
    tag: str
    name: str | None = None
    breed: str | None = None
    breed_variant: str | None = None
    breed_id: UUID | None = None  # optional FK
    birth_date: date | None = None
    lot: str | None = None
    lot_id: UUID | None = None  # optional FK
    status_id: UUID | None = None
    photo_url: str | None = None


class AnimalCreate(AnimalBase):
    # Legacy support: allow status code string
    status: str | None = None


class AnimalUpdate(BaseModel):
    version: int
    name: str | None = None
    breed: str | None = None
    breed_variant: str | None = None
    breed_id: UUID | None = None
    birth_date: date | None = None
    lot: str | None = None
    lot_id: UUID | None = None
    status_id: UUID | None = None
    # Legacy support: allow status code string
    status: str | None = None
    photo_url: str | None = None


class AnimalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    tag: str
    name: str | None
    breed: str | None
    breed_variant: str | None = None
    breed_id: UUID | None = None
    birth_date: date | None
    lot: str | None
    lot_id: UUID | None = None
    status_id: UUID | None
    # Derived fields
    status_code: str | None = None
    status: str | None = None
    status_desc: str | None = None
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
