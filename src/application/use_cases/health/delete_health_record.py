from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from src.application.interfaces.unit_of_work import UnitOfWork


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    record_id: UUID,
) -> None:
    """Soft delete a health record."""

    record = await uow.health_records.get(tenant_id, record_id)
    if not record:
        raise ValueError(f"Health record {record_id} not found")

    record.deleted_at = datetime.now(timezone.utc)
    await uow.health_records.delete(record)
