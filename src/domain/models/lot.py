from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(slots=True)
class Lot:
    id: UUID
    tenant_id: UUID
    name: str
    active: bool = True
    notes: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        name: str,
        *,
        active: bool = True,
        notes: str | None = None,
    ) -> Lot:
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            active=active,
            notes=notes,
            created_at=datetime.now(timezone.utc),
        )
