from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.models.access_request import AccessRequest
from src.domain.value_objects.access_request_status import AccessRequestStatus


class AccessRequestsRepository(Protocol):
    async def add(self, request: AccessRequest) -> AccessRequest: ...

    async def get(self, request_id: UUID) -> AccessRequest | None: ...

    async def find_open_by_email(self, email: str) -> AccessRequest | None: ...

    async def list(
        self,
        *,
        status: AccessRequestStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[AccessRequest], int]: ...

    async def update(self, request: AccessRequest) -> AccessRequest: ...
