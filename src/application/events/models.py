from __future__ import annotations

from dataclasses import dataclass
from datetime import date
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
    date: date


@dataclass(frozen=True)
class ProductionRecordedEvent:
    tenant_id: UUID
    actor_user_id: UUID
    production_id: UUID
    animal_id: UUID
    volume_l: float | str
    shift: str
    date: date


@dataclass(frozen=True)
class ProductionLowEvent:
    tenant_id: UUID
    actor_user_id: UUID
    production_id: UUID
    animal_id: UUID
    volume_l: float | str
    avg_hist: float | str
    shift: str
    date: date


@dataclass(frozen=True)
class ProductionBulkRecordedEvent:
    tenant_id: UUID
    actor_user_id: UUID
    count: int
    total_volume_l: float | str
    shift: str
    date: date
