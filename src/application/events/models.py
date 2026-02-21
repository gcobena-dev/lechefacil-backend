from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID


@dataclass(frozen=True)
class DeliveryRecordedEvent:
    tenant_id: UUID
    actor_user_id: UUID
    delivery_id: UUID
    buyer_id: UUID
    volume_l: float | str
    amount: float | str
    currency: str
    date_time: datetime | None = None


@dataclass(frozen=True)
class ProductionRecordedEvent:
    tenant_id: UUID
    actor_user_id: UUID
    production_id: UUID
    animal_id: UUID
    volume_l: float | str
    shift: str
    date_time: datetime | None = None


@dataclass(frozen=True)
class ProductionLowEvent:
    tenant_id: UUID
    actor_user_id: UUID
    production_id: UUID
    animal_id: UUID
    volume_l: float | str
    avg_hist: float | str
    shift: str
    date_time: datetime | None = None


@dataclass(frozen=True)
class ProductionBulkRecordedEvent:
    tenant_id: UUID
    actor_user_id: UUID
    count: int
    total_volume_l: float | str
    shift: str
    date_time: datetime | None = None


@dataclass(frozen=True)
class AnimalCreatedEvent:
    tenant_id: UUID
    actor_user_id: UUID
    animal_id: UUID
    tag: str
    name: str | None = None


@dataclass(frozen=True)
class AnimalUpdatedEvent:
    tenant_id: UUID
    actor_user_id: UUID
    animal_id: UUID
    tag: str
    name: str | None = None
    changed_fields: list[str] | None = None


@dataclass(frozen=True)
class AnimalEventCreatedEvent:
    tenant_id: UUID
    actor_user_id: UUID
    animal_id: UUID
    event_id: UUID
    event_type: str
    occurred_at: datetime | None = None
    tag: str | None = None
    name: str | None = None
    event_data: dict | None = None


@dataclass(frozen=True)
class PregnancyCheckRecordedEvent:
    tenant_id: UUID
    actor_user_id: UUID
    insemination_id: UUID
    animal_id: UUID
    result: str  # CONFIRMED, OPEN, LOST
    check_date: datetime
    checked_by: str | None = None
    tag: str | None = None
    name: str | None = None
    expected_calving_date: date | None = None


@dataclass(frozen=True)
class SemenStockLowEvent:
    tenant_id: UUID
    actor_user_id: UUID
    sire_catalog_id: UUID
    sire_name: str
    current_quantity: int
    batch_code: str | None = None
