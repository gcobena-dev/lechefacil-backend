from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from uuid import UUID, uuid4


class InseminationMethod(str, Enum):
    AI = "AI"
    NATURAL = "NATURAL"
    ET = "ET"
    IATF = "IATF"


class PregnancyStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    OPEN = "OPEN"
    LOST = "LOST"


GESTATION_DAYS = 283


@dataclass(slots=True)
class Insemination:
    id: UUID
    tenant_id: UUID
    animal_id: UUID
    service_date: datetime
    method: str

    sire_catalog_id: UUID | None = None
    semen_inventory_id: UUID | None = None
    service_event_id: UUID | None = None
    technician: str | None = None
    straw_count: int = 1
    heat_detected: bool = False
    protocol: str | None = None
    pregnancy_status: str = PregnancyStatus.PENDING.value
    pregnancy_check_date: datetime | None = None
    pregnancy_checked_by: str | None = None
    expected_calving_date: date | None = None
    calving_event_id: UUID | None = None
    notes: str | None = None

    deleted_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        animal_id: UUID,
        service_date: datetime,
        method: str,
        sire_catalog_id: UUID | None = None,
        semen_inventory_id: UUID | None = None,
        service_event_id: UUID | None = None,
        technician: str | None = None,
        straw_count: int = 1,
        heat_detected: bool = False,
        protocol: str | None = None,
        notes: str | None = None,
    ) -> Insemination:
        now = datetime.now(timezone.utc)
        if service_date.tzinfo is None:
            service_date = service_date.replace(tzinfo=timezone.utc)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            animal_id=animal_id,
            service_date=service_date,
            method=method,
            sire_catalog_id=sire_catalog_id,
            semen_inventory_id=semen_inventory_id,
            service_event_id=service_event_id,
            technician=technician,
            straw_count=straw_count,
            heat_detected=heat_detected,
            protocol=protocol,
            notes=notes,
            created_at=now,
            updated_at=now,
            version=1,
        )

    def confirm_pregnancy(
        self,
        check_date: datetime,
        checked_by: str | None = None,
    ) -> None:
        self.pregnancy_status = PregnancyStatus.CONFIRMED.value
        self.pregnancy_check_date = check_date
        self.pregnancy_checked_by = checked_by
        self.expected_calving_date = (self.service_date + timedelta(days=GESTATION_DAYS)).date()
        self.bump_version()

    def mark_open(
        self,
        check_date: datetime,
        checked_by: str | None = None,
    ) -> None:
        self.pregnancy_status = PregnancyStatus.OPEN.value
        self.pregnancy_check_date = check_date
        self.pregnancy_checked_by = checked_by
        self.expected_calving_date = None
        self.bump_version()

    def mark_lost(
        self,
        check_date: datetime,
        checked_by: str | None = None,
    ) -> None:
        self.pregnancy_status = PregnancyStatus.LOST.value
        self.pregnancy_check_date = check_date
        self.pregnancy_checked_by = checked_by
        self.expected_calving_date = None
        self.bump_version()

    def bump_version(self) -> None:
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)
