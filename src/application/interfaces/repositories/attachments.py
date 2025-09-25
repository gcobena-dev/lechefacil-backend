from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.models.attachment import Attachment
from src.domain.value_objects.owner_type import OwnerType


class AttachmentsRepository(Protocol):
    async def add(self, attachment: Attachment) -> Attachment: ...

    async def list_for_owner(
        self, tenant_id: UUID, owner_type: OwnerType, owner_id: UUID
    ) -> list[Attachment]: ...

    async def get(self, tenant_id: UUID, attachment_id: UUID) -> Attachment | None: ...

    async def set_primary(
        self, tenant_id: UUID, owner_type: OwnerType, owner_id: UUID, attachment_id: UUID
    ) -> None: ...

    async def update_metadata(
        self,
        tenant_id: UUID,
        attachment_id: UUID,
        *,
        title: str | None = None,
        description: str | None = None,
        position: int | None = None,
        is_primary: bool | None = None,
    ) -> Attachment | None: ...

    async def soft_delete(self, tenant_id: UUID, attachment_id: UUID) -> bool: ...

    async def count_for_owner(
        self, tenant_id: UUID, owner_type: OwnerType, owner_id: UUID
    ) -> int: ...

    async def get_primary_for_owner(
        self, tenant_id: UUID, owner_type: OwnerType, owner_id: UUID
    ) -> Attachment | None: ...
