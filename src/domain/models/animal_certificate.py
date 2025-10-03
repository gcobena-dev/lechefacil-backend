from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from uuid import UUID, uuid4


@dataclass(slots=True)
class AnimalCertificate:
    id: UUID
    tenant_id: UUID
    animal_id: UUID
    registry_number: str | None = None
    bolus_id: str | None = None
    tattoo_left: str | None = None
    tattoo_right: str | None = None
    issue_date: date | None = None
    breeder: str | None = None
    owner: str | None = None
    farm: str | None = None
    certificate_name: str | None = None
    association_code: str | None = None
    notes: str | None = None
    data: dict | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1

    @classmethod
    def create(
        cls,
        tenant_id: UUID,
        animal_id: UUID,
        registry_number: str | None = None,
        bolus_id: str | None = None,
        tattoo_left: str | None = None,
        tattoo_right: str | None = None,
        issue_date: date | None = None,
        breeder: str | None = None,
        owner: str | None = None,
        farm: str | None = None,
        certificate_name: str | None = None,
        association_code: str | None = None,
        notes: str | None = None,
        data: dict | None = None,
    ) -> AnimalCertificate:
        now = datetime.now(timezone.utc)
        return cls(
            id=uuid4(),
            tenant_id=tenant_id,
            animal_id=animal_id,
            registry_number=registry_number,
            bolus_id=bolus_id,
            tattoo_left=tattoo_left,
            tattoo_right=tattoo_right,
            issue_date=issue_date,
            breeder=breeder,
            owner=owner,
            farm=farm,
            certificate_name=certificate_name,
            association_code=association_code,
            notes=notes,
            data=data,
            created_at=now,
            updated_at=now,
            version=1,
        )

    def bump_version(self) -> None:
        self.version += 1
        self.updated_at = datetime.now(timezone.utc)
