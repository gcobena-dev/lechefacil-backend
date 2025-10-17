from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.health_record import HealthRecord


@dataclass
class UpdateHealthRecordInput:
    record_id: UUID
    occurred_at: datetime | None = None
    veterinarian: str | None = None
    cost: Decimal | None = None
    notes: str | None = None
    vaccine_name: str | None = None
    next_dose_date: date | None = None
    medication: str | None = None
    duration_days: int | None = None
    withdrawal_days: int | None = None


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    payload: UpdateHealthRecordInput,
) -> HealthRecord:
    """Update a health record."""

    record = await uow.health_records.get(tenant_id, payload.record_id)
    if not record:
        raise ValueError(f"Health record {payload.record_id} not found")

    # Update fields (only if provided)
    if payload.occurred_at is not None:
        record.occurred_at = payload.occurred_at
    if payload.veterinarian is not None:
        record.veterinarian = payload.veterinarian
    if payload.cost is not None:
        record.cost = payload.cost
    if payload.notes is not None:
        record.notes = payload.notes
    if payload.vaccine_name is not None:
        record.vaccine_name = payload.vaccine_name
    if payload.next_dose_date is not None:
        record.next_dose_date = payload.next_dose_date
    if payload.medication is not None:
        record.medication = payload.medication
    if payload.duration_days is not None:
        record.duration_days = payload.duration_days
    if payload.withdrawal_days is not None:
        record.withdrawal_days = payload.withdrawal_days

        # Recalculate withdrawal_until if treatment
        if record.event_type == "TREATMENT" and record.duration_days:
            end_treatment = record.occurred_at.date() + timedelta(days=record.duration_days)
            record.withdrawal_until = end_treatment + timedelta(days=record.withdrawal_days)

            # Update animal withdrawal
            animal = await uow.animals.get(tenant_id, record.animal_id)
            if animal:
                animal.in_milk_withdrawal = True
                animal.withdrawal_until = record.withdrawal_until
                animal.bump_version()
                await uow.animals.update(animal)

    record.bump_version()
    await uow.health_records.update(record)

    return record
