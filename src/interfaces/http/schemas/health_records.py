from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HealthRecordCreate(BaseModel):
    """Schema for creating health records.

    Event types:
    - VACCINATION: { vaccine_name, next_dose_date?, veterinarian?, cost?, notes? }
    - TREATMENT: { medication, duration_days?, withdrawal_days?, veterinarian?, cost?, notes? }
    - VET_OBSERVATION: { veterinarian?, cost?, notes? }
    - EMERGENCY: { veterinarian?, cost?, notes? }
    """

    event_type: str = Field(
        ...,
        description="Event type: VACCINATION, TREATMENT, VET_OBSERVATION, EMERGENCY",
    )
    occurred_at: datetime

    # Common fields
    veterinarian: str | None = None
    cost: Decimal | None = None
    notes: str | None = None

    # Vaccination fields
    vaccine_name: str | None = None
    next_dose_date: date | None = None

    # Treatment fields
    medication: str | None = None
    duration_days: int | None = None
    withdrawal_days: int | None = None

    @field_validator("event_type")
    def validate_type(cls, v):
        valid_types = {"VACCINATION", "TREATMENT", "VET_OBSERVATION", "EMERGENCY"}
        if v not in valid_types:
            raise ValueError(f"Invalid event type. Must be one of: {', '.join(valid_types)}")
        return v

    @field_validator("occurred_at")
    def ensure_aware_utc(cls, v: datetime) -> datetime:
        """Ensure `occurred_at` is timezone-aware and in UTC."""
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)


class HealthRecordUpdate(BaseModel):
    """Schema for updating health records."""

    occurred_at: datetime | None = None
    veterinarian: str | None = None
    cost: Decimal | None = None
    notes: str | None = None
    vaccine_name: str | None = None
    next_dose_date: date | None = None
    medication: str | None = None
    duration_days: int | None = None
    withdrawal_days: int | None = None

    @field_validator("occurred_at")
    def ensure_aware_utc(cls, v: datetime | None) -> datetime | None:
        """Ensure `occurred_at` is timezone-aware and in UTC."""
        if v is None:
            return None
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)


class HealthRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    animal_id: UUID
    event_type: str
    occurred_at: datetime

    # Common fields
    veterinarian: str | None
    cost: Decimal | None
    notes: str | None

    # Vaccination fields
    vaccine_name: str | None
    next_dose_date: date | None

    # Treatment fields
    medication: str | None
    duration_days: int | None
    withdrawal_days: int | None
    withdrawal_until: date | None

    # Audit
    created_at: datetime
    updated_at: datetime
    version: int


class HealthRecordListResponse(BaseModel):
    items: list[HealthRecordResponse]
    total: int
    limit: int
    offset: int


class AttachmentInfo(BaseModel):
    """Simplified attachment info for frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    url: str
    mime_type: str
    size_bytes: int | None
    is_image: bool = False


class HealthRecordWithAttachments(HealthRecordResponse):
    """Health record with attached files."""

    attachments: list[AttachmentInfo] = []
