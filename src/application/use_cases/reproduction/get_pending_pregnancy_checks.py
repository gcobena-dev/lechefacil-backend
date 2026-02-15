from __future__ import annotations

from uuid import UUID

from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.models.insemination import Insemination


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    min_days: int = 35,
    max_days: int = 50,
) -> list[Insemination]:
    return await uow.inseminations.get_pending_checks(
        tenant_id, min_days=min_days, max_days=max_days
    )
