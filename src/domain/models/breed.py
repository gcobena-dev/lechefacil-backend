from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(slots=True)
class Breed:
    id: UUID
    tenant_id: UUID | None
    name: str
    code: str | None
    is_system_default: bool
    active: bool = True
    metadata: dict | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        name: str,
        *,
        tenant_id: UUID | None = None,
        code: str | None = None,
        is_system_default: bool = False,
        active: bool = True,
        metadata: dict | None = None,
    ) -> Breed:
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            code=code,
            is_system_default=is_system_default,
            active=active,
            metadata=metadata,
            created_at=datetime.now(timezone.utc),
        )
