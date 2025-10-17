from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4


class HealthEventType(str, Enum):
    VACCINATION = "VACCINATION"
    TREATMENT = "TREATMENT"
    VET_OBSERVATION = "VET_OBSERVATION"
    EMERGENCY = "EMERGENCY"


@dataclass(slots=True)
class HealthRecord:
    id: UUID
    tenant_id: UUID
    animal_id: UUID
    event_type: str  # HealthEventType
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
    withdrawal_until: date | None = None

    # Audit fields
    # Note: Attachments are stored in the 'attachments' table with owner_type='HEALTH_EVENT'
    deleted_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        animal_id: UUID,
        event_type: str,
        occurred_at: datetime,
        veterinarian: str | None = None,
        cost: Decimal | None = None,
        notes: str | None = None,
        vaccine_name: str | None = None,
        next_dose_date: date | None = None,
        medication: str | None = None,
        duration_days: int | None = None,
        withdrawal_days: int | None = None,
        withdrawal_until: date | None = None,
    ) -> HealthRecord:
        now = datetime.now(timezone.utc)

        # Ensure occurred_at is timezone-aware and in UTC
        if occurred_at.tzinfo is None or occurred_at.tzinfo.utcoffset(occurred_at) is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)
        else:
            occurred_at = occurred_at.astimezone(timezone.utc)

        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            animal_id=animal_id,
            event_type=event_type,
            occurred_at=occurred_at,
            veterinarian=veterinarian,
            cost=cost,
            notes=notes,
            vaccine_name=vaccine_name,
            next_dose_date=next_dose_date,
            medication=medication,
            duration_days=duration_days,
            withdrawal_days=withdrawal_days,
            withdrawal_until=withdrawal_until,
            created_at=now,
            updated_at=now,
            version=1,
        )

    def bump_version(self) -> None:
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)
