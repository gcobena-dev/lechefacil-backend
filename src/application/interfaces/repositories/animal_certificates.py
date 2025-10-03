from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.models.animal_certificate import AnimalCertificate


class AnimalCertificatesRepository(Protocol):
    async def add(self, certificate: AnimalCertificate) -> AnimalCertificate: ...

    async def get(self, tenant_id: UUID, certificate_id: UUID) -> AnimalCertificate | None: ...

    async def get_by_animal(self, tenant_id: UUID, animal_id: UUID) -> AnimalCertificate | None: ...

    async def update(self, certificate: AnimalCertificate) -> AnimalCertificate: ...

    async def delete(self, tenant_id: UUID, animal_id: UUID) -> bool: ...
