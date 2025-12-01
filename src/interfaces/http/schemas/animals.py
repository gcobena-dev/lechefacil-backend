from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    labels: list[str] = Field(default_factory=list, max_length=6)

    # Genealogy fields
    sex: str | None = None
    dam_id: UUID | None = None
    sire_id: UUID | None = None
    external_sire_code: str | None = None
    external_sire_registry: str | None = None

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, v: list[str]) -> list[str]:
        if len(v) > 6:
            raise ValueError("Maximum 6 labels allowed")

        # Normalize and validate each label
        normalized = []
        for label in v:
            # Remove special characters, keep only alphanumeric
            clean_label = "".join(c for c in label if c.isalnum() or c.isspace()).strip()
            if not clean_label:
                continue
            # Max 30 characters per label
            if len(clean_label) > 30:
                raise ValueError("Each label must be 30 characters or less")
            normalized.append(clean_label)

        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for label in normalized:
            label_lower = label.lower()
            if label_lower not in seen:
                seen.add(label_lower)
                unique.append(label)

        return unique


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
    labels: list[str] | None = None

    # Genealogy fields
    sex: str | None = None
    dam_id: UUID | None = None
    sire_id: UUID | None = None
    external_sire_code: str | None = None
    external_sire_registry: str | None = None

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        if len(v) > 6:
            raise ValueError("Maximum 6 labels allowed")

        # Normalize and validate each label
        normalized = []
        for label in v:
            # Remove special characters, keep only alphanumeric
            clean_label = "".join(c for c in label if c.isalnum() or c.isspace()).strip()
            if not clean_label:
                continue
            # Max 30 characters per label
            if len(clean_label) > 30:
                raise ValueError("Each label must be 30 characters or less")
            normalized.append(clean_label)

        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for label in normalized:
            label_lower = label.lower()
            if label_lower not in seen:
                seen.add(label_lower)
                unique.append(label)

        return unique


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
    labels: list[str]

    # Genealogy fields
    sex: str | None = None
    dam_id: UUID | None = None
    sire_id: UUID | None = None
    external_sire_code: str | None = None
    external_sire_registry: str | None = None

    # Disposition fields (read-only, set by events)
    disposition_at: datetime | None = None
    disposition_reason: str | None = None

    created_at: datetime
    updated_at: datetime
    version: int
    # Derived fields for attachments (optional in responses)
    primary_photo_url: str | None = None
    primary_photo_signed_url: str | None = None
    photos_count: int | None = None


class AnimalsListResponse(BaseModel):
    items: list[AnimalResponse]
    next_cursor: str | None = None
    total: int | None = None


class AnimalValueResponse(BaseModel):
    animal_id: UUID
    date: date
    total_volume_l: Decimal
    price_per_l: Decimal
    currency: str
    amount: Decimal
    source: str  # deliveries_average | price_daily | tenant_default
