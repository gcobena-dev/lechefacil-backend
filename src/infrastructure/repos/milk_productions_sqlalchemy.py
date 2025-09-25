from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories.milk_productions import MilkProductionsRepository
from src.domain.models.milk_production import MilkProduction
from src.infrastructure.db.orm.milk_production import MilkProductionORM


class MilkProductionsSQLAlchemyRepository(MilkProductionsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: MilkProductionORM) -> MilkProduction:
        return MilkProduction(
            id=orm.id,
            tenant_id=orm.tenant_id,
            animal_id=orm.animal_id,
            buyer_id=orm.buyer_id,
            date_time=orm.date_time,
            date=orm.date,
            input_unit=orm.input_unit,
            input_quantity=orm.input_quantity,
            density=orm.density,
            volume_l=orm.volume_l,
            price_snapshot=orm.price_snapshot,
            currency=orm.currency,
            amount=orm.amount,
            notes=orm.notes,
            deleted_at=orm.deleted_at,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            version=orm.version,
        )

    async def add(self, mp: MilkProduction) -> MilkProduction:
        orm = MilkProductionORM(
            id=mp.id,
            tenant_id=mp.tenant_id,
            animal_id=mp.animal_id,
            buyer_id=mp.buyer_id,
            date_time=mp.date_time,
            date=mp.date,
            input_unit=mp.input_unit,
            input_quantity=mp.input_quantity,
            density=mp.density,
            volume_l=mp.volume_l,
            price_snapshot=mp.price_snapshot,
            currency=mp.currency,
            amount=mp.amount,
            notes=mp.notes,
            deleted_at=mp.deleted_at,
            created_at=mp.created_at,
            updated_at=mp.updated_at,
            version=mp.version,
        )
        self.session.add(orm)
        await self.session.flush()
        return self._to_domain(orm)

    async def get(self, tenant_id: UUID, production_id: UUID) -> MilkProduction | None:
        result = await self.session.execute(
            select(MilkProductionORM).where(
                MilkProductionORM.tenant_id == tenant_id,
                MilkProductionORM.id == production_id,
                MilkProductionORM.deleted_at.is_(None),
            )
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list(
        self,
        tenant_id: UUID,
        *,
        date_from: date | None,
        date_to: date | None,
        animal_id: UUID | None,
    ) -> list[MilkProduction]:
        conds = [MilkProductionORM.tenant_id == tenant_id, MilkProductionORM.deleted_at.is_(None)]
        if date_from:
            conds.append(MilkProductionORM.date >= date_from)
        if date_to:
            conds.append(MilkProductionORM.date <= date_to)
        if animal_id is not None:
            conds.append(MilkProductionORM.animal_id == animal_id)
        result = await self.session.execute(select(MilkProductionORM).where(and_(*conds)))
        return [self._to_domain(r) for r in result.scalars().all()]

    async def update(
        self, tenant_id: UUID, production_id: UUID, data: dict
    ) -> MilkProduction | None:
        stmt = (
            update(MilkProductionORM)
            .where(MilkProductionORM.tenant_id == tenant_id, MilkProductionORM.id == production_id)
            .values(**data)
            .returning(MilkProductionORM)
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def delete(self, tenant_id: UUID, production_id: UUID) -> bool:
        from sqlalchemy import func

        stmt = (
            update(MilkProductionORM)
            .where(MilkProductionORM.tenant_id == tenant_id, MilkProductionORM.id == production_id)
            .values(deleted_at=func.now())
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0
