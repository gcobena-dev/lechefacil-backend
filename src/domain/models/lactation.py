from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from uuid import UUID, uuid4


@dataclass(slots=True)
class Lactation:
    id: UUID
    tenant_id: UUID
    animal_id: UUID
    number: int
    start_date: date
    end_date: date | None = None
    status: str = "open"  # 'open' | 'closed'
    calving_event_id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        animal_id: UUID,
        number: int,
        start_date: date,
        calving_event_id: UUID | None = None,
    ) -> Lactation:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            animal_id=animal_id,
            number=number,
            start_date=start_date,
            status="open",
            calving_event_id=calving_event_id,
            created_at=now,
            updated_at=now,
            version=1,
        )

    def close(self, end_date: date) -> None:
        self.status = "closed"
        self.end_date = end_date
        self.bump_version()

    def bump_version(self) -> None:
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)
