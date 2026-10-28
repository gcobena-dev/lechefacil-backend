from __future__ import annotations

from datetime import date, datetime
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


class HerdBullCandidate(BaseModel):
    """A male of the herd that is not in the sire catalog yet."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tag: str
    name: str | None
    breed: str | None
    birth_date: date | None


class ImportFromHerdRequest(BaseModel):
    animal_ids: list[UUID]


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


class SirePerformanceSummaryItemResponse(BaseModel):
    sire: SireCatalogResponse
    total_inseminations: int
    confirmed_pregnancies: int
    conception_rate: float
    straws_used: int
    straws_in_stock: int


class SirePerformanceSummaryResponse(BaseModel):
    items: list[SirePerformanceSummaryItemResponse]
    date_from: datetime
    date_to: datetime
    include_inactive: bool
