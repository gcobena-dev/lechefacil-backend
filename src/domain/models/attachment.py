from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.domain.value_objects.owner_type import OwnerType


@dataclass(slots=True)
class Attachment:
    id: UUID
    tenant_id: UUID
    owner_type: OwnerType
    owner_id: UUID
    kind: str  # e.g. "photo", "document"
    title: str | None = None
    description: str | None = None
    storage_key: str = ""
    mime_type: str = ""
    size_bytes: int | None = None
    checksum: str | None = None
    width: int | None = None
    height: int | None = None
    is_primary: bool = False
    position: int = 0
    deleted_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        owner_type: OwnerType,
        owner_id: UUID,
        kind: str,
        storage_key: str,
        mime_type: str,
        size_bytes: int | None = None,
        title: str | None = None,
        description: str | None = None,
        is_primary: bool = False,
        position: int = 0,
    ) -> Attachment:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            owner_type=owner_type,
            owner_id=owner_id,
            kind=kind,
            title=title,
            description=description,
            storage_key=storage_key,
            mime_type=mime_type,
            size_bytes=size_bytes,
            is_primary=is_primary,
            position=position,
            created_at=now,
            updated_at=now,
            version=1,
        )
