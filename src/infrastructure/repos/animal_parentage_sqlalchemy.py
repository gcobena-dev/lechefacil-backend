from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories.animal_parentage import (
    AnimalParentageRepository,
)
from src.domain.models.animal_parentage import AnimalParentage
from src.infrastructure.db.orm.animal_parentage import AnimalParentageORM


class AnimalParentageSQLAlchemyRepository(AnimalParentageRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: AnimalParentageORM) -> AnimalParentage:
        return AnimalParentage(
            id=orm.id,
            tenant_id=orm.tenant_id,
            child_id=orm.child_id,
            relation=orm.relation,
            parent_animal_id=orm.parent_animal_id,
            external_code=orm.external_code,
            external_registry=orm.external_registry,
            source=orm.source,
            effective_from=orm.effective_from,
            data=orm.data,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            version=orm.version,
        )

    def _to_orm(self, parentage: AnimalParentage) -> AnimalParentageORM:
        return AnimalParentageORM(
            id=parentage.id,
            tenant_id=parentage.tenant_id,
            child_id=parentage.child_id,
            relation=parentage.relation,
            parent_animal_id=parentage.parent_animal_id,
            external_code=parentage.external_code,
            external_registry=parentage.external_registry,
            source=parentage.source,
            effective_from=parentage.effective_from,
            data=parentage.data,
            created_at=parentage.created_at,
            updated_at=parentage.updated_at,
            version=parentage.version,
        )

    async def add(self, parentage: AnimalParentage) -> AnimalParentage:
        orm = self._to_orm(parentage)
        self.session.add(orm)
        await self.session.flush()
        return self._to_domain(orm)

    async def get_current(
        self, tenant_id: UUID, child_id: UUID, relation: str
    ) -> AnimalParentage | None:
        stmt = (
            select(AnimalParentageORM)
            .where(AnimalParentageORM.tenant_id == tenant_id)
            .where(AnimalParentageORM.child_id == child_id)
            .where(AnimalParentageORM.relation == relation)
            .order_by(AnimalParentageORM.effective_from.desc().nulls_last())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_by_child(self, tenant_id: UUID, child_id: UUID) -> list[AnimalParentage]:
        stmt = (
            select(AnimalParentageORM)
            .where(AnimalParentageORM.tenant_id == tenant_id)
            .where(AnimalParentageORM.child_id == child_id)
            .order_by(AnimalParentageORM.relation, AnimalParentageORM.effective_from.desc())
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def set_current(
        self,
        child_id: UUID,
        relation: str,
        parent_animal_id: UUID | None = None,
        external_code: str | None = None,
        external_registry: str | None = None,
    ) -> AnimalParentage:
        """Set or update the current parentage. This method is a placeholder
        that should be implemented with proper tenant_id handling."""
        raise NotImplementedError(
            "set_current should be called through a service with proper tenant context"
        )
