from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories.lactations import LactationsRepository
from src.domain.models.lactation import Lactation
from src.infrastructure.db.orm.lactation import LactationORM
from src.infrastructure.db.orm.milk_production import MilkProductionORM


class LactationsSQLAlchemyRepository(LactationsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: LactationORM) -> Lactation:
        return Lactation(
            id=orm.id,
            tenant_id=orm.tenant_id,
            animal_id=orm.animal_id,
            number=orm.number,
            start_date=orm.start_date,
            end_date=orm.end_date,
            status=orm.status,
            calving_event_id=orm.calving_event_id,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            version=orm.version,
        )

    def _to_orm(self, lactation: Lactation) -> LactationORM:
        return LactationORM(
            id=lactation.id,
            tenant_id=lactation.tenant_id,
            animal_id=lactation.animal_id,
            number=lactation.number,
            start_date=lactation.start_date,
            end_date=lactation.end_date,
            status=lactation.status,
            calving_event_id=lactation.calving_event_id,
            created_at=lactation.created_at,
            updated_at=lactation.updated_at,
            version=lactation.version,
        )

    async def add(self, lactation: Lactation) -> Lactation:
        orm = self._to_orm(lactation)
        self.session.add(orm)
        await self.session.flush()
        return self._to_domain(orm)

    async def get(self, tenant_id: UUID, lactation_id: UUID) -> Lactation | None:
        stmt = (
            select(LactationORM)
            .where(LactationORM.tenant_id == tenant_id)
            .where(LactationORM.id == lactation_id)
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_open(self, tenant_id: UUID, animal_id: UUID) -> Lactation | None:
        stmt = (
            select(LactationORM)
            .where(LactationORM.tenant_id == tenant_id)
            .where(LactationORM.animal_id == animal_id)
            .where(LactationORM.status == "open")
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_last_number(self, tenant_id: UUID, animal_id: UUID) -> int:
        stmt = (
            select(func.max(LactationORM.number))
            .where(LactationORM.tenant_id == tenant_id)
            .where(LactationORM.animal_id == animal_id)
        )
        result = await self.session.execute(stmt)
        max_number = result.scalar_one_or_none()
        return max_number or 0

    async def list_by_animal(self, tenant_id: UUID, animal_id: UUID) -> list[Lactation]:
        stmt = (
            select(LactationORM)
            .where(LactationORM.tenant_id == tenant_id)
            .where(LactationORM.animal_id == animal_id)
            .order_by(LactationORM.number.desc())
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def update(self, lactation: Lactation) -> Lactation:
        stmt = (
            select(LactationORM)
            .where(LactationORM.tenant_id == lactation.tenant_id)
            .where(LactationORM.id == lactation.id)
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm:
            orm.status = lactation.status
            orm.end_date = lactation.end_date
            orm.updated_at = lactation.updated_at
            orm.version = lactation.version
            await self.session.flush()
            return self._to_domain(orm)

        raise ValueError(f"Lactation {lactation.id} not found")

    async def sum_volume(self, lactation_id: UUID) -> float:
        stmt = select(func.sum(MilkProductionORM.volume_l)).where(
            MilkProductionORM.lactation_id == lactation_id
        )
        result = await self.session.execute(stmt)
        total = result.scalar_one_or_none()
        return float(total) if total else 0.0

    async def find_by_date(
        self, tenant_id: UUID, animal_id: UUID, target_date: date
    ) -> Lactation | None:
        """Find a lactation that includes the given date.

        A date is included if:
        - start_date <= target_date AND (end_date is NULL OR end_date >= target_date)
        """
        stmt = (
            select(LactationORM)
            .where(LactationORM.tenant_id == tenant_id)
            .where(LactationORM.animal_id == animal_id)
            .where(LactationORM.start_date <= target_date)
            .where(
                or_(
                    LactationORM.end_date.is_(None),
                    LactationORM.end_date >= target_date,
                )
            )
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None
