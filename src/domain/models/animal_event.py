from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class AnimalEventType(str, Enum):
    BIRTH = "BIRTH"
    CALVING = "CALVING"
    DRY_OFF = "DRY_OFF"
    SALE = "SALE"
    DEATH = "DEATH"
    CULL = "CULL"
    SERVICE = "SERVICE"
    EMBRYO_TRANSFER = "EMBRYO_TRANSFER"
    ABORTION = "ABORTION"
    TRANSFER = "TRANSFER"


@dataclass(slots=True)
class AnimalEvent:
    id: UUID
    tenant_id: UUID
    animal_id: UUID
    type: str
    occurred_at: datetime
    data: dict | None = None
    parent_event_id: UUID | None = None
    new_status_id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        animal_id: UUID,
        type: str,
        occurred_at: datetime,
        data: dict | None = None,
        parent_event_id: UUID | None = None,
        new_status_id: UUID | None = None,
    ) -> AnimalEvent:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            animal_id=animal_id,
            type=type,
            occurred_at=occurred_at,
            data=data,
            parent_event_id=parent_event_id,
            new_status_id=new_status_id,
            created_at=now,
            updated_at=now,
            version=1,
        )

    def bump_version(self) -> None:
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)
