from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from uuid import UUID, uuid4


class ParentageRelation(str, Enum):
    DAM = "DAM"  # Mother
    SIRE = "SIRE"  # Father
    RECIPIENT = "RECIPIENT"  # Embryo transfer recipient
    DONOR = "DONOR"  # Embryo donor


@dataclass(slots=True)
class AnimalParentage:
    id: UUID
    tenant_id: UUID
    child_id: UUID
    relation: str  # ParentageRelation
    parent_animal_id: UUID | None = None  # local animal (if exists in system)
    external_code: str | None = None  # external sire/dam code
    external_registry: str | None = None  # registry name (e.g., "HOLSTEIN_USA")
    source: str = "manual"  # 'manual' | 'event' | 'import'
    effective_from: date | None = None
    data: dict | None = None  # additional metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        child_id: UUID,
        relation: str,
        parent_animal_id: UUID | None = None,
        external_code: str | None = None,
        external_registry: str | None = None,
        source: str = "manual",
        effective_from: date | None = None,
        data: dict | None = None,
    ) -> AnimalParentage:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            child_id=child_id,
            relation=relation,
            parent_animal_id=parent_animal_id,
            external_code=external_code,
            external_registry=external_registry,
            source=source,
            effective_from=effective_from,
            data=data,
            created_at=now,
            updated_at=now,
            version=1,
        )

    def bump_version(self) -> None:
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)
