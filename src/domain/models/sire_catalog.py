from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(slots=True)
class SireCatalog:
    id: UUID
    tenant_id: UUID
    name: str
    short_code: str | None = None
    registry_code: str | None = None
    registry_name: str | None = None
    breed_id: UUID | None = None
    animal_id: UUID | None = None
    is_active: bool = True
    genetic_notes: str | None = None
    data: dict | None = None

    deleted_at: datetime | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        name: str,
        short_code: str | None = None,
        registry_code: str | None = None,
        registry_name: str | None = None,
        breed_id: UUID | None = None,
        animal_id: UUID | None = None,
        genetic_notes: str | None = None,
        data: dict | None = None,
    ) -> SireCatalog:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            short_code=short_code,
            registry_code=registry_code,
            registry_name=registry_name,
            breed_id=breed_id,
            animal_id=animal_id,
            genetic_notes=genetic_notes,
            data=data,
            created_at=now,
            updated_at=now,
            version=1,
        )

    def bump_version(self) -> None:
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)
