from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.domain.models.insemination import Insemination


class InseminationsRepository(Protocol):
    async def add(self, insemination: Insemination) -> Insemination: ...

    async def update(self, insemination: Insemination) -> Insemination: ...

    async def get(self, tenant_id: UUID, insemination_id: UUID) -> Insemination | None: ...

    async def list(
        self,
        tenant_id: UUID,
        animal_id: UUID | None = None,
        sire_catalog_id: UUID | None = None,
        pregnancy_status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Insemination]: ...

    async def count(
        self,
        tenant_id: UUID,
        animal_id: UUID | None = None,
        sire_catalog_id: UUID | None = None,
        pregnancy_status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int: ...

    async def get_pending_checks(
        self,
        tenant_id: UUID,
        min_days: int = 35,
        max_days: int = 50,
    ) -> list[Insemination]: ...

    async def get_latest_confirmed(
        self,
        tenant_id: UUID,
        animal_id: UUID,
    ) -> Insemination | None: ...

    async def count_by_sire(
        self,
        tenant_id: UUID,
        sire_catalog_id: UUID,
    ) -> int: ...

    async def count_confirmed_by_sire(
        self,
        tenant_id: UUID,
        sire_catalog_id: UUID,
    ) -> int: ...

    async def delete(self, insemination: Insemination) -> None: ...
