from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SireCatalogCreate(BaseModel):
    name: str
    short_code: str | None = None
    registry_code: str | None = None
    registry_name: str | None = None
    breed_id: UUID | None = None
    animal_id: UUID | None = None
    genetic_notes: str | None = None
    data: dict | None = None


class SireCatalogUpdate(BaseModel):
    name: str | None = None
    short_code: str | None = None
    registry_code: str | None = None
    registry_name: str | None = None
    breed_id: UUID | None = None
    animal_id: UUID | None = None
    is_active: bool | None = None
    genetic_notes: str | None = None
    data: dict | None = None


class SireCatalogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    short_code: str | None
    registry_code: str | None
    registry_name: str | None
    breed_id: UUID | None
    animal_id: UUID | None
    is_active: bool
    genetic_notes: str | None
    data: dict | None
    created_at: datetime
    updated_at: datetime
    version: int


class SireCatalogListResponse(BaseModel):
    items: list[SireCatalogResponse]
    total: int
    limit: int
    offset: int


class SirePerformanceResponse(BaseModel):
    sire: SireCatalogResponse
    total_inseminations: int
    confirmed_pregnancies: int
    conception_rate: float
