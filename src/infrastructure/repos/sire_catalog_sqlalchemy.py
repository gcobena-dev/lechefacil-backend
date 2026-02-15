from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.sire_catalog import SireCatalog
from src.infrastructure.db.orm.sire_catalog import SireCatalogORM


class SireCatalogSQLAlchemyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: SireCatalogORM) -> SireCatalog:
        return SireCatalog(
            id=orm.id,
            tenant_id=orm.tenant_id,
            name=orm.name,
            short_code=orm.short_code,
            registry_code=orm.registry_code,
            registry_name=orm.registry_name,
            breed_id=orm.breed_id,
            animal_id=orm.animal_id,
            is_active=orm.is_active,
            genetic_notes=orm.genetic_notes,
            data=orm.data,
            deleted_at=orm.deleted_at,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            version=orm.version,
        )

    async def add(self, sire: SireCatalog) -> SireCatalog:
        orm = SireCatalogORM(
            id=sire.id,
            tenant_id=sire.tenant_id,
            name=sire.name,
            short_code=sire.short_code,
            registry_code=sire.registry_code,
            registry_name=sire.registry_name,
            breed_id=sire.breed_id,
            animal_id=sire.animal_id,
            is_active=sire.is_active,
            genetic_notes=sire.genetic_notes,
            data=sire.data,
            created_at=sire.created_at,
            updated_at=sire.updated_at,
            version=sire.version,
        )
        self.session.add(orm)
        await self.session.flush()
        return self._to_domain(orm)

    async def update(self, sire: SireCatalog) -> SireCatalog:
        orm = await self.session.get(SireCatalogORM, sire.id)
        if not orm:
            raise ValueError(f"SireCatalog {sire.id} not found")
        orm.name = sire.name
        orm.short_code = sire.short_code
        orm.registry_code = sire.registry_code
        orm.registry_name = sire.registry_name
        orm.breed_id = sire.breed_id
        orm.animal_id = sire.animal_id
        orm.is_active = sire.is_active
        orm.genetic_notes = sire.genetic_notes
        orm.data = sire.data
        orm.updated_at = sire.updated_at
        orm.version = sire.version
        await self.session.flush()
        return self._to_domain(orm)

    async def get(self, tenant_id: UUID, sire_id: UUID) -> SireCatalog | None:
        stmt = (
            select(SireCatalogORM)
            .where(SireCatalogORM.tenant_id == tenant_id)
            .where(SireCatalogORM.id == sire_id)
            .where(SireCatalogORM.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list(
        self,
        tenant_id: UUID,
        active_only: bool = True,
        search: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[SireCatalog]:
        stmt = (
            select(SireCatalogORM)
            .where(SireCatalogORM.tenant_id == tenant_id)
            .where(SireCatalogORM.deleted_at.is_(None))
            .order_by(SireCatalogORM.name)
            .offset(offset)
        )
        if active_only:
            stmt = stmt.where(SireCatalogORM.is_active.is_(True))
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    SireCatalogORM.name.ilike(pattern),
                    SireCatalogORM.short_code.ilike(pattern),
                    SireCatalogORM.registry_code.ilike(pattern),
                )
            )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def count(
        self,
        tenant_id: UUID,
        active_only: bool = True,
        search: str | None = None,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(SireCatalogORM)
            .where(SireCatalogORM.tenant_id == tenant_id)
            .where(SireCatalogORM.deleted_at.is_(None))
        )
        if active_only:
            stmt = stmt.where(SireCatalogORM.is_active.is_(True))
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    SireCatalogORM.name.ilike(pattern),
                    SireCatalogORM.short_code.ilike(pattern),
                    SireCatalogORM.registry_code.ilike(pattern),
                )
            )
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def delete(self, sire: SireCatalog) -> None:
        orm = await self.session.get(SireCatalogORM, sire.id)
        if orm:
            orm.deleted_at = sire.deleted_at
