from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class InseminationCreate(BaseModel):
    animal_id: UUID
    service_date: datetime
    method: str  # AI, NATURAL, ET, IATF
    sire_catalog_id: UUID | None = None
    semen_inventory_id: UUID | None = None
    technician: str | None = None
    straw_count: int = 1
    heat_detected: bool = False
    protocol: str | None = None
    notes: str | None = None

    @field_validator("service_date")
    def ensure_aware_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)


class InseminationUpdate(BaseModel):
    technician: str | None = None
    notes: str | None = None
    heat_detected: bool | None = None
    protocol: str | None = None


class PregnancyCheckInput(BaseModel):
    result: str  # CONFIRMED, OPEN, LOST
    check_date: datetime
    checked_by: str | None = None

    @field_validator("check_date")
    def ensure_aware_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)


class InseminationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    animal_id: UUID
    animal_tag: str | None = None
    animal_name: str | None = None
    sire_catalog_id: UUID | None
    semen_inventory_id: UUID | None
    service_event_id: UUID | None
    service_date: datetime
    method: str
    technician: str | None
    straw_count: int
    heat_detected: bool
    protocol: str | None
    pregnancy_status: str
    pregnancy_check_date: datetime | None
    pregnancy_checked_by: str | None
    expected_calving_date: date | None
    calving_event_id: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    version: int


class InseminationListResponse(BaseModel):
    items: list[InseminationResponse]
    total: int
    limit: int
    offset: int
