from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import and_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.errors import ConflictError
from src.application.interfaces.repositories.milk_prices import MilkPricesRepository
from src.domain.models.milk_price import MilkPrice
from src.infrastructure.db.orm.milk_price import MilkPriceDailyORM


class MilkPricesSQLAlchemyRepository(MilkPricesRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: MilkPriceDailyORM) -> MilkPrice:
        return MilkPrice(
            id=orm.id,
            tenant_id=orm.tenant_id,
            date=orm.date,
            price_per_l=orm.price_per_l,
            currency=orm.currency,
            buyer_id=orm.buyer_id,
            deleted_at=orm.deleted_at,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            version=orm.version,
        )

    async def add(self, price: MilkPrice) -> MilkPrice:
        orm = MilkPriceDailyORM(
            id=price.id,
            tenant_id=price.tenant_id,
            date=price.date,
            price_per_l=price.price_per_l,
            currency=price.currency,
            buyer_id=price.buyer_id,
            deleted_at=price.deleted_at,
            created_at=price.created_at,
            updated_at=price.updated_at,
            version=price.version,
        )
        self.session.add(orm)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError("Price already exists for date/buyer") from exc
        return self._to_domain(orm)

    async def update(self, tenant_id: UUID, price_id: UUID, data: dict) -> MilkPrice | None:
        stmt = (
            update(MilkPriceDailyORM)
            .where(
                MilkPriceDailyORM.tenant_id == tenant_id,
                MilkPriceDailyORM.id == price_id,
            )
            .values(**data)
            .returning(MilkPriceDailyORM)
        )
        try:
            result = await self.session.execute(stmt)
        except IntegrityError as exc:
            raise ConflictError("Price conflicts with existing entry") from exc
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def delete(self, tenant_id: UUID, price_id: UUID) -> bool:
        from sqlalchemy import func

        stmt = (
            update(MilkPriceDailyORM)
            .where(
                MilkPriceDailyORM.tenant_id == tenant_id,
                MilkPriceDailyORM.id == price_id,
            )
            .values(deleted_at=func.now())
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def list(
        self,
        tenant_id: UUID,
        *,
        date_from: date | None,
        date_to: date | None,
        buyer_id: UUID | None,
    ) -> list[MilkPrice]:
        conds = [MilkPriceDailyORM.tenant_id == tenant_id]
        if date_from:
            conds.append(MilkPriceDailyORM.date >= date_from)
        if date_to:
            conds.append(MilkPriceDailyORM.date <= date_to)
        if buyer_id is not None:
            conds.append(MilkPriceDailyORM.buyer_id == buyer_id)
        result = await self.session.execute(select(MilkPriceDailyORM).where(and_(*conds)))
        return [self._to_domain(r) for r in result.scalars().all()]

    async def get_for_date(
        self, tenant_id: UUID, the_date: date, buyer_id: UUID | None
    ) -> MilkPrice | None:
        conds = [
            MilkPriceDailyORM.tenant_id == tenant_id,
            MilkPriceDailyORM.date == the_date,
        ]
        if buyer_id is None:
            conds.append(MilkPriceDailyORM.buyer_id.is_(None))
        else:
            conds.append(MilkPriceDailyORM.buyer_id == buyer_id)
        result = await self.session.execute(select(MilkPriceDailyORM).where(and_(*conds)))
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_existing(
        self, tenant_id: UUID, the_date: date, buyer_id: UUID | None
    ) -> MilkPrice | None:
        return await self.get_for_date(tenant_id, the_date, buyer_id)

    async def get_most_recent(self, tenant_id: UUID) -> MilkPrice | None:
        stmt = (
            select(MilkPriceDailyORM)
            .where(MilkPriceDailyORM.tenant_id == tenant_id)
            .order_by(MilkPriceDailyORM.date.desc(), MilkPriceDailyORM.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None
