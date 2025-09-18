from __future__ import annotations

from datetime import date, datetime
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


class AnimalsListResponse(BaseModel):
    items: list[AnimalResponse]
    next_cursor: str | None = None
