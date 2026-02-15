from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SemenInventoryCreate(BaseModel):
    sire_catalog_id: UUID
    initial_quantity: int
    batch_code: str | None = None
    tank_id: str | None = None
    canister_position: str | None = None
    supplier: str | None = None
    cost_per_straw: Decimal | None = None
    currency: str = "USD"
    purchase_date: date | None = None
    expiry_date: date | None = None
    notes: str | None = None


class SemenInventoryUpdate(BaseModel):
    batch_code: str | None = None
    tank_id: str | None = None
    canister_position: str | None = None
    current_quantity: int | None = None
    supplier: str | None = None
    cost_per_straw: Decimal | None = None
    currency: str | None = None
    purchase_date: date | None = None
    expiry_date: date | None = None
    notes: str | None = None


class SemenInventoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    sire_catalog_id: UUID
    batch_code: str | None
    tank_id: str | None
    canister_position: str | None
    initial_quantity: int
    current_quantity: int
    supplier: str | None
    cost_per_straw: Decimal | None
    currency: str
    purchase_date: date | None
    expiry_date: date | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    version: int


class SemenInventoryListResponse(BaseModel):
    items: list[SemenInventoryResponse]
    total: int
    limit: int
    offset: int
