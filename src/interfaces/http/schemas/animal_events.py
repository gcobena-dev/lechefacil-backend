from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.utils.datetime_tz import to_utc


class AnimalEventCreate(BaseModel):
    """Schema for creating animal events.

    Event types and their required data fields:
    - CALVING: { mother_lot_id?: UUID, calf?: { tag, sex, name?, birth_weight?,
    breed?, breed_id?, breed_variant?, lot_id?, sire_id?, sire_catalog_id?,
    external_sire_code?, external_sire_registry? } }. Manages lactations, status
    and services; the calf's sire defaults to the bull of the credited service.
    - DRY_OFF: No extra data required (DRY, or PREGNANT_DRY if pregnant)
    - SALE: { buyer?: string, price?: number, notes?: string }
    - DEATH: { cause?: string, notes?: string }
    - CULL: { reason: string, notes?: string }
    - SERVICE: { sire_id?: UUID, external_sire_code?: string,
    external_sire_registry?: string, method?: string }
    - EMBRYO_TRANSFER: { donor_id?: UUID, recipient_id?: UUID, embryo_code?: string }
    - BIRTH: { calf_tag: string, calf_sex: string, calf_name?: string, birth_weight?: number,
    breed?: string, breed_variant?: string, breed_id?: UUID, current_lot_id?: UUID }
    - ABORTION: { cause?: string, gestation_days?: number }
    - TRANSFER: { from_lot?: string, to_lot?: string, reason?: string }
    """

    type: str = Field(
        ...,
        description="Event type: CALVING, DRY_OFF, SALE, DEATH, CULL, "
        "SERVICE, EMBRYO_TRANSFER, BIRTH, ABORTION, TRANSFER",
    )
    occurred_at: datetime
    data: dict | None = None

    @field_validator("type")
    def validate_type(cls, v):
        valid_types = {
            "CALVING",
            "DRY_OFF",
            "SALE",
            "DEATH",
            "CULL",
            "SERVICE",
            "EMBRYO_TRANSFER",
            "BIRTH",
            "ABORTION",
            "TRANSFER",
        }
        if v not in valid_types:
            raise ValueError(f"Invalid event type. Must be one of: {', '.join(valid_types)}")
        return v

    @field_validator("occurred_at")
    def ensure_aware_utc(cls, v: datetime) -> datetime:
        """Normalize `occurred_at` to UTC.

        A naive value is what the user typed in the event form, i.e. Ecuador
        time. App builds before 0.0.987 send it that way, so it must not be
        read as UTC (that stored every event 5 hours early).
        """
        return to_utc(v)


class AnimalEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    animal_id: UUID
    type: str
    occurred_at: datetime
    data: dict | None
    parent_event_id: UUID | None
    new_status_id: UUID | None
    created_at: datetime
    updated_at: datetime
    version: int


class AnimalEventsListResponse(BaseModel):
    items: list[AnimalEventResponse]
    total: int
    page: int
    per_page: int


class AnimalEventEffects(BaseModel):
    """Effects produced by an event."""

    event: AnimalEventResponse
    lactation_opened: UUID | None = None
    lactation_closed: UUID | None = None
    new_status_id: UUID | None = None
    new_status_code: str | None = None
    calf_created: UUID | None = None
    parentage_created: list[UUID] | None = None
    disposition_set: bool = False
    message: str | None = None


class BirthEventData(BaseModel):
    """Structured data for BIRTH events."""

    calf_tag: str
    calf_sex: str  # 'MALE' | 'FEMALE'
    calf_name: str | None = None
    birth_weight: float | None = None
    assisted: bool = False
    notes: str | None = None
    # Breed information
    breed: str | None = None
    breed_variant: str | None = None
    breed_id: UUID | None = None
    # Lot assignment
    current_lot_id: UUID | None = None


class ServiceEventData(BaseModel):
    """Structured data for SERVICE/EMBRYO_TRANSFER events.

    Services recorded through /reproduction store nothing here: the record
    lives in `inseminations` and the fields below are resolved from it on every
    read, so an edit there shows up on the timeline immediately. They are only
    stored for events that have no insemination behind them (imported herds,
    events predating the reproduction module), where this *is* the record.
    """

    insemination_id: UUID | None = None  # The record these values were read from
    sire_id: UUID | None = None  # Local sire (an animal of the herd)
    sire_catalog_id: UUID | None = None  # Bull from the sire catalog
    sire_name: str | None = None  # Sire name, for display
    sire_code: str | None = None  # Its short code (registry code as fallback)
    external_sire_code: str | None = None
    external_sire_registry: str | None = None
    method: str | None = None  # 'AI' | 'NATURAL' | 'ET'
    technician: str | None = None
    notes: str | None = None


class DispositionEventData(BaseModel):
    """Structured data for SALE/DEATH/CULL events."""

    reason: str
    buyer: str | None = None  # For SALE
    price: float | None = None  # For SALE
    cause: str | None = None  # For DEATH
    notes: str | None = None
