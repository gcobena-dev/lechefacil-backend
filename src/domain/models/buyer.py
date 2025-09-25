from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(slots=True)
class Buyer:
    id: UUID
    tenant_id: UUID
    name: str
    code: str | None = None
    contact: str | None = None
    is_active: bool = True
    deleted_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    @classmethod
    def create(
        cls,
        *,
        tenant_id: UUID,
        name: str,
        code: str | None = None,
        contact: str | None = None,
        is_active: bool = True,
    ) -> Buyer:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            code=code,
            contact=contact,
            is_active=is_active,
            created_at=now,
            updated_at=now,
            version=1,
        )
