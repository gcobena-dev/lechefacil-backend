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
    breed_variant: str | None = None
    breed_id: UUID | None = None
    birth_date: date | None = None
    lot: str | None = None
    current_lot_id: UUID | None = None
    status_id: UUID | None = None
    photo_url: str | None = None

    # Genealogy fields
    sex: str | None = None
    dam_id: UUID | None = None
    sire_id: UUID | None = None
    external_sire_code: str | None = None
    external_sire_registry: str | None = None

    # Disposition fields
    disposition_at: datetime | None = None
    disposition_reason: str | None = None

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
        breed_variant: str | None = None,
        breed_id: UUID | None = None,
        birth_date: date | None = None,
        lot: str | None = None,
        current_lot_id: UUID | None = None,
        status_id: UUID | None = None,
        photo_url: str | None = None,
        sex: str | None = None,
        dam_id: UUID | None = None,
        sire_id: UUID | None = None,
        external_sire_code: str | None = None,
        external_sire_registry: str | None = None,
    ) -> Animal:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            tag=tag,
            name=name,
            breed=breed,
            breed_variant=breed_variant,
            breed_id=breed_id,
            birth_date=birth_date,
            lot=lot,
            current_lot_id=current_lot_id,
            status_id=status_id,
            photo_url=photo_url,
            sex=sex,
            dam_id=dam_id,
            sire_id=sire_id,
            external_sire_code=external_sire_code,
            external_sire_registry=external_sire_registry,
            created_at=now,
            updated_at=now,
            version=1,
        )

    def bump_version(self) -> None:
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)
