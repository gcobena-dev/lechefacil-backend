from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories.animal_certificates import (
    AnimalCertificatesRepository,
)
from src.domain.models.animal_certificate import AnimalCertificate
from src.infrastructure.db.orm.animal_certificate import AnimalCertificateORM


class AnimalCertificatesSQLAlchemyRepository(AnimalCertificatesRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: AnimalCertificateORM) -> AnimalCertificate:
        return AnimalCertificate(
            id=orm.id,
            tenant_id=orm.tenant_id,
            animal_id=orm.animal_id,
            registry_number=orm.registry_number,
            bolus_id=orm.bolus_id,
            tattoo_left=orm.tattoo_left,
            tattoo_right=orm.tattoo_right,
            issue_date=orm.issue_date,
            breeder=orm.breeder,
            owner=orm.owner,
            farm=orm.farm,
            data=orm.data,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            version=orm.version,
        )

    def _to_orm(self, certificate: AnimalCertificate) -> AnimalCertificateORM:
        return AnimalCertificateORM(
            id=certificate.id,
            tenant_id=certificate.tenant_id,
            animal_id=certificate.animal_id,
            registry_number=certificate.registry_number,
            bolus_id=certificate.bolus_id,
            tattoo_left=certificate.tattoo_left,
            tattoo_right=certificate.tattoo_right,
            issue_date=certificate.issue_date,
            breeder=certificate.breeder,
            owner=certificate.owner,
            farm=certificate.farm,
            data=certificate.data,
            created_at=certificate.created_at,
            updated_at=certificate.updated_at,
            version=certificate.version,
        )

    async def add(self, certificate: AnimalCertificate) -> AnimalCertificate:
        orm = self._to_orm(certificate)
        self.session.add(orm)
        await self.session.flush()
        return self._to_domain(orm)

    async def get(self, tenant_id: UUID, certificate_id: UUID) -> AnimalCertificate | None:
        stmt = (
            select(AnimalCertificateORM)
            .where(AnimalCertificateORM.tenant_id == tenant_id)
            .where(AnimalCertificateORM.id == certificate_id)
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_animal(self, tenant_id: UUID, animal_id: UUID) -> AnimalCertificate | None:
        stmt = (
            select(AnimalCertificateORM)
            .where(AnimalCertificateORM.tenant_id == tenant_id)
            .where(AnimalCertificateORM.animal_id == animal_id)
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def update(self, certificate: AnimalCertificate) -> AnimalCertificate:
        stmt = (
            select(AnimalCertificateORM)
            .where(AnimalCertificateORM.tenant_id == certificate.tenant_id)
            .where(AnimalCertificateORM.id == certificate.id)
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm:
            orm.registry_number = certificate.registry_number
            orm.bolus_id = certificate.bolus_id
            orm.tattoo_left = certificate.tattoo_left
            orm.tattoo_right = certificate.tattoo_right
            orm.issue_date = certificate.issue_date
            orm.breeder = certificate.breeder
            orm.owner = certificate.owner
            orm.farm = certificate.farm
            orm.data = certificate.data
            orm.updated_at = certificate.updated_at
            orm.version = certificate.version
            await self.session.flush()
            return self._to_domain(orm)

        raise ValueError(f"Certificate {certificate.id} not found")

    async def delete(self, tenant_id: UUID, animal_id: UUID) -> bool:
        stmt = delete(AnimalCertificateORM).where(
            AnimalCertificateORM.tenant_id == tenant_id,
            AnimalCertificateORM.animal_id == animal_id,
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
