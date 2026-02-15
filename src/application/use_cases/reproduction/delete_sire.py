from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from src.application.errors import NotFound
from src.application.interfaces.unit_of_work import UnitOfWork


async def execute(
    uow: UnitOfWork,
    tenant_id: UUID,
    sire_id: UUID,
) -> None:
    sire = await uow.sire_catalog.get(tenant_id, sire_id)
    if not sire:
        raise NotFound(f"Sire {sire_id} not found")
    sire.deleted_at = datetime.now(timezone.utc)
    await uow.sire_catalog.delete(sire)
