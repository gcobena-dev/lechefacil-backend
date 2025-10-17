from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.health_record import HealthRecord


@dataclass
class CreateHealthRecordInput:
    animal_id: UUID
    event_type: str
    occurred_at: datetime
    veterinarian: str | None = None
    cost: Decimal | None = None
    notes: str | None = None
    vaccine_name: str | None = None
    next_dose_date: date | None = None
    medication: str | None = None
    duration_days: int | None = None
    withdrawal_days: int | None = None


@dataclass
class CreateHealthRecordOutput:
    health_record: HealthRecord
    animal_updated: bool = False  # True if withdrawal was set


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    payload: CreateHealthRecordInput,
) -> CreateHealthRecordOutput:
    """Create a health record and update animal withdrawal if needed."""

    # Calculate withdrawal_until if it's a treatment with withdrawal
    withdrawal_until = None
    if payload.event_type == "TREATMENT" and payload.withdrawal_days and payload.duration_days:
        end_treatment = payload.occurred_at.date() + timedelta(days=payload.duration_days)
        withdrawal_until = end_treatment + timedelta(days=payload.withdrawal_days)

    # Create health record
    record = HealthRecord.create(
        tenant_id=tenant_id,
        animal_id=payload.animal_id,
        event_type=payload.event_type,
        occurred_at=payload.occurred_at,
        veterinarian=payload.veterinarian,
        cost=payload.cost,
        notes=payload.notes,
        vaccine_name=payload.vaccine_name,
        next_dose_date=payload.next_dose_date,
        medication=payload.medication,
        duration_days=payload.duration_days,
        withdrawal_days=payload.withdrawal_days,
        withdrawal_until=withdrawal_until,
    )

    await uow.health_records.add(record)

    # Update animal if withdrawal period
    animal_updated = False
    if withdrawal_until:
        animal = await uow.animals.get(tenant_id, payload.animal_id)
        if animal:
            animal.in_milk_withdrawal = True
            animal.withdrawal_until = withdrawal_until
            animal.bump_version()
            await uow.animals.update(animal)
            animal_updated = True

    return CreateHealthRecordOutput(
        health_record=record,
        animal_updated=animal_updated,
    )
