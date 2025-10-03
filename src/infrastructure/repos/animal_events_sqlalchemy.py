from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories.animal_events import AnimalEventsRepository
from src.domain.models.animal_event import AnimalEvent
from src.infrastructure.db.orm.animal_event import AnimalEventORM


class AnimalEventsSQLAlchemyRepository(AnimalEventsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: AnimalEventORM) -> AnimalEvent:
        return AnimalEvent(
            id=orm.id,
            tenant_id=orm.tenant_id,
            animal_id=orm.animal_id,
            type=orm.type,
            occurred_at=orm.occurred_at,
            data=orm.data,
            parent_event_id=orm.parent_event_id,
            new_status_id=orm.new_status_id,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            version=orm.version,
        )

    def _to_orm(self, event: AnimalEvent) -> AnimalEventORM:
        return AnimalEventORM(
            id=event.id,
            tenant_id=event.tenant_id,
            animal_id=event.animal_id,
            type=event.type,
            occurred_at=event.occurred_at,
            data=event.data,
            parent_event_id=event.parent_event_id,
            new_status_id=event.new_status_id,
            created_at=event.created_at,
            updated_at=event.updated_at,
            version=event.version,
        )

    async def add(self, event: AnimalEvent) -> AnimalEvent:
        orm = self._to_orm(event)
        self.session.add(orm)
        await self.session.flush()
        return self._to_domain(orm)

    async def get(self, tenant_id: UUID, event_id: UUID) -> AnimalEvent | None:
        stmt = (
            select(AnimalEventORM)
            .where(AnimalEventORM.tenant_id == tenant_id)
            .where(AnimalEventORM.id == event_id)
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_by_animal(self, tenant_id: UUID, animal_id: UUID) -> list[AnimalEvent]:
        stmt = (
            select(AnimalEventORM)
            .where(AnimalEventORM.tenant_id == tenant_id)
            .where(AnimalEventORM.animal_id == animal_id)
            .order_by(AnimalEventORM.occurred_at.desc())
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def list_by_animal_paginated(
        self, tenant_id: UUID, animal_id: UUID, offset: int, limit: int
    ) -> list[AnimalEvent]:
        stmt = (
            select(AnimalEventORM)
            .where(AnimalEventORM.tenant_id == tenant_id)
            .where(AnimalEventORM.animal_id == animal_id)
            .order_by(AnimalEventORM.occurred_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def count_by_animal(self, tenant_id: UUID, animal_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(AnimalEventORM)
            .where(AnimalEventORM.tenant_id == tenant_id)
            .where(AnimalEventORM.animal_id == animal_id)
        )
        result = await self.session.execute(stmt)
        count = result.scalar_one()
        return int(count or 0)

    async def last_of_type(
        self, tenant_id: UUID, animal_id: UUID, event_type: str
    ) -> AnimalEvent | None:
        stmt = (
            select(AnimalEventORM)
            .where(AnimalEventORM.tenant_id == tenant_id)
            .where(AnimalEventORM.animal_id == animal_id)
            .where(AnimalEventORM.type == event_type)
            .order_by(AnimalEventORM.occurred_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None
