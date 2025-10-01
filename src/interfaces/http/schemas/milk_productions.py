from __future__ import annotations

from datetime import date as DtDate
from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MilkProductionCreate(BaseModel):
    # Preferred simple inputs
    date: DtDate | None = None
    shift: Literal["AM", "PM"] | None = "AM"
    # Advanced override (if provided, ignores date/shift)
    date_time: datetime | None = None
    # Required association to animal
    animal_id: UUID
    input_unit: str = Field(pattern="^(kg|lb|l)$")
    input_quantity: Decimal
    density: Decimal | None = None
    buyer_id: UUID | None = None
    notes: str | None = None


class MilkProductionUpdate(BaseModel):
    version: int
    # You may update via date/shift or date_time directly
    date: DtDate | None = None
    shift: Literal["AM", "PM"] | None = None
    date_time: datetime | None = None
    animal_id: UUID | None = None
    buyer_id: UUID | None = None
    input_unit: str | None = None
    input_quantity: Decimal | None = None
    density: Decimal | None = None
    notes: str | None = None


class MilkProductionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    animal_id: UUID | None
    buyer_id: UUID | None
    date_time: datetime
    shift: str
    input_unit: str
    input_quantity: Decimal
    density: Decimal
    volume_l: Decimal
    price_snapshot: Decimal | None
    currency: str
    amount: Decimal | None
    notes: str | None
    version: int
    created_at: datetime
    updated_at: datetime


class MilkProductionBulkItem(BaseModel):
    animal_id: UUID
    input_quantity: Decimal


class MilkProductionsBulkCreate(BaseModel):
    # Shared fields for the whole batch
    date: DtDate | None = None
    shift: Literal["AM", "PM"] | None = "AM"
    date_time: datetime | None = None
    input_unit: str | None = Field(default=None, pattern="^(kg|lb|l)$")
    density: Decimal | None = None
    buyer_id: UUID | None = None
    notes: str | None = None
    # Items with only animal and quantity
    items: list[MilkProductionBulkItem]


class MilkProductionListResponse(BaseModel):
    items: list[MilkProductionResponse]
    total: int
    limit: int
    offset: int


# OCR-related schemas
class ProcessOcrRequest(BaseModel):
    storage_key: str
    mime_type: str
    size_bytes: int | None = None


class OcrMatchedResult(BaseModel):
    animal_id: UUID
    animal_name: str
    animal_tag: str
    liters: Decimal
    match_confidence: float
    extracted_name: str


class OcrUnmatchedResult(BaseModel):
    extracted_name: str
    liters: Decimal
    suggestions: list[dict] = Field(default_factory=list)


class ProcessOcrResponse(BaseModel):
    image_url: str
    attachment_id: UUID
    matched: list[OcrMatchedResult]
    unmatched: list[OcrUnmatchedResult]
    total_extracted: int
