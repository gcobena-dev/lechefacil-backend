from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.models.tenant_config import TenantConfig


class TenantConfigRepository(Protocol):
    async def get(self, tenant_id: UUID) -> TenantConfig | None: ...
    async def upsert(self, config: TenantConfig) -> TenantConfig: ...
    async def update(self, tenant_id: UUID, data: dict) -> TenantConfig | None: ...
