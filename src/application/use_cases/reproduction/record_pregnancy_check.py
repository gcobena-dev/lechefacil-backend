from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from src.application.errors import NotFound, ValidationError
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.insemination import Insemination, PregnancyStatus


@dataclass(slots=True)
class RecordPregnancyCheckInput:
    insemination_id: UUID
    result: str  # CONFIRMED, OPEN, LOST
    check_date: datetime
    checked_by: str | None = None


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    payload: RecordPregnancyCheckInput,
) -> Insemination:
    valid_results = {
        PregnancyStatus.CONFIRMED.value,
        PregnancyStatus.OPEN.value,
        PregnancyStatus.LOST.value,
    }
    if payload.result not in valid_results:
        raise ValidationError(f"Invalid result. Must be one of: {', '.join(valid_results)}")

    insemination = await uow.inseminations.get(tenant_id, payload.insemination_id)
    if not insemination:
        raise NotFound(f"Insemination {payload.insemination_id} not found")

    check_date = payload.check_date
    if check_date.tzinfo is None:
        check_date = check_date.replace(tzinfo=timezone.utc)

    if payload.result == PregnancyStatus.CONFIRMED.value:
        insemination.confirm_pregnancy(check_date, payload.checked_by)
    elif payload.result == PregnancyStatus.OPEN.value:
        insemination.mark_open(check_date, payload.checked_by)
    elif payload.result == PregnancyStatus.LOST.value:
        insemination.mark_lost(check_date, payload.checked_by)

    return await uow.inseminations.update(insemination)
