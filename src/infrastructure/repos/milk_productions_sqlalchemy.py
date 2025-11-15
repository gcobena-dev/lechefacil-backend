from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import and_, func, select, update
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
            lactation_id=orm.lactation_id,
            date_time=orm.date_time,
            date=orm.date,
            shift=orm.shift,
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
            lactation_id=mp.lactation_id,
            date_time=mp.date_time,
            date=mp.date,
            shift=mp.shift,
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
        order_by: str | None = None,
        order: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[MilkProduction]:
        from sqlalchemy import asc, desc

        from src.infrastructure.db.orm.animal import AnimalORM

        conds = [MilkProductionORM.tenant_id == tenant_id, MilkProductionORM.deleted_at.is_(None)]
        if date_from:
            conds.append(MilkProductionORM.date >= date_from)
        if date_to:
            conds.append(MilkProductionORM.date <= date_to)
        if animal_id is not None:
            conds.append(MilkProductionORM.animal_id == animal_id)
        stmt = select(MilkProductionORM).where(and_(*conds))
        # Determine ordering
        ob = (order_by or "recent").lower()
        od = (order or "desc").lower()
        dir_fn = desc if od == "desc" else asc
        if ob == "volume":
            stmt = stmt.order_by(dir_fn(MilkProductionORM.volume_l), dir_fn(MilkProductionORM.id))
        elif ob == "name":
            # Join animal to order by name/tag
            stmt = stmt.join(
                AnimalORM,
                and_(
                    AnimalORM.id == MilkProductionORM.animal_id,
                    AnimalORM.tenant_id == MilkProductionORM.tenant_id,
                ),
                isouter=True,
            ).order_by(dir_fn(AnimalORM.name), dir_fn(AnimalORM.tag), dir_fn(MilkProductionORM.id))
        elif ob == "code":
            # Order by animal tag (code), then name
            stmt = stmt.join(
                AnimalORM,
                and_(
                    AnimalORM.id == MilkProductionORM.animal_id,
                    AnimalORM.tenant_id == MilkProductionORM.tenant_id,
                ),
                isouter=True,
            ).order_by(dir_fn(AnimalORM.tag), dir_fn(AnimalORM.name), dir_fn(MilkProductionORM.id))
        else:
            # Default: most recent first
            stmt = stmt.order_by(dir_fn(MilkProductionORM.date_time), dir_fn(MilkProductionORM.id))
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)
        result = await self.session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def count(
        self,
        tenant_id: UUID,
        *,
        date_from: date | None,
        date_to: date | None,
        animal_id: UUID | None,
    ) -> int:
        conds = [MilkProductionORM.tenant_id == tenant_id, MilkProductionORM.deleted_at.is_(None)]
        if date_from:
            conds.append(MilkProductionORM.date >= date_from)
        if date_to:
            conds.append(MilkProductionORM.date <= date_to)
        if animal_id is not None:
            conds.append(MilkProductionORM.animal_id == animal_id)
        stmt = select(func.count()).select_from(MilkProductionORM).where(and_(*conds))
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

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
