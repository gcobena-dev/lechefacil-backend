from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from src.application.interfaces.unit_of_work import UnitOfWork
from src.application.patching import resolve_patch
from src.domain.models.health_record import HealthRecord

#: Columns that may be blanked out. `occurred_at` is NOT NULL, so it is absent.
CLEARABLE_FIELDS = frozenset(
    {
        "veterinarian",
        "cost",
        "notes",
        "vaccine_name",
        "next_dose_date",
        "medication",
        "duration_days",
        "withdrawal_days",
    }
)

PATCHABLE_FIELDS = ("occurred_at", *sorted(CLEARABLE_FIELDS))


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
    #: Field names the client actually sent. Without it a `null` meaning "clear
    #: this" is indistinguishable from a field that was simply left out.
    fields_set: frozenset[str] = frozenset()


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    payload: UpdateHealthRecordInput,
) -> HealthRecord:
    """Update a health record."""

    record = await uow.health_records.get(tenant_id, payload.record_id)
    if not record:
        raise ValueError(f"Health record {payload.record_id} not found")

    # Only what the client sent, nulls included so a field can be cleared.
    patch = resolve_patch(
        payload,
        PATCHABLE_FIELDS,
        sent=payload.fields_set,
        nullable=CLEARABLE_FIELDS,
    )
    for name, value in patch.items():
        setattr(record, name, value)

    if "withdrawal_days" in patch and record.withdrawal_days is None:
        # The withdrawal was removed, so the date derived from it goes with it.
        record.withdrawal_until = None
    elif "withdrawal_days" in patch:
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
