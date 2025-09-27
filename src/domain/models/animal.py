from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from uuid import UUID, uuid4


@dataclass(slots=True)
class Animal:
    id: UUID
    tenant_id: UUID
    tag: str
    name: str | None = None
    breed: str | None = None
    birth_date: date | None = None
    lot: str | None = None
    status_id: UUID | None = None
    photo_url: str | None = None
    deleted_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        tag: str,
        name: str | None = None,
        breed: str | None = None,
        birth_date: date | None = None,
        lot: str | None = None,
        status_id: UUID | None = None,
        photo_url: str | None = None,
    ) -> Animal:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            tag=tag,
            name=name,
            breed=breed,
            birth_date=birth_date,
            lot=lot,
            status_id=status_id,
            photo_url=photo_url,
            created_at=now,
            updated_at=now,
            version=1,
        )

    def bump_version(self) -> None:
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)
