from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import and_, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories.milk_deliveries import MilkDeliveriesRepository
from src.domain.models.milk_delivery import MilkDelivery
from src.infrastructure.db.orm.milk_delivery import MilkDeliveryORM


class MilkDeliveriesSQLAlchemyRepository(MilkDeliveriesRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: MilkDeliveryORM) -> MilkDelivery:
        return MilkDelivery(
            id=orm.id,
            tenant_id=orm.tenant_id,
            buyer_id=orm.buyer_id,
            date_time=orm.date_time,
            date=orm.date,
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

    async def add(self, md: MilkDelivery) -> MilkDelivery:
        orm = MilkDeliveryORM(
            id=md.id,
            tenant_id=md.tenant_id,
            buyer_id=md.buyer_id,
            date_time=md.date_time,
            date=md.date,
            volume_l=md.volume_l,
            price_snapshot=md.price_snapshot,
            currency=md.currency,
            amount=md.amount,
            notes=md.notes,
            deleted_at=md.deleted_at,
            created_at=md.created_at,
            updated_at=md.updated_at,
            version=md.version,
        )
        self.session.add(orm)
        await self.session.flush()
        return self._to_domain(orm)

    async def get(self, tenant_id: UUID, delivery_id: UUID) -> MilkDelivery | None:
        result = await self.session.execute(
            select(MilkDeliveryORM).where(
                MilkDeliveryORM.tenant_id == tenant_id,
                MilkDeliveryORM.id == delivery_id,
                MilkDeliveryORM.deleted_at.is_(None),
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
        buyer_id: UUID | None,
    ) -> list[MilkDelivery]:
        conds = [MilkDeliveryORM.tenant_id == tenant_id, MilkDeliveryORM.deleted_at.is_(None)]
        if date_from:
            conds.append(MilkDeliveryORM.date >= date_from)
        if date_to:
            conds.append(MilkDeliveryORM.date <= date_to)
        if buyer_id is not None:
            conds.append(MilkDeliveryORM.buyer_id == buyer_id)
        result = await self.session.execute(select(MilkDeliveryORM).where(and_(*conds)))
        return [self._to_domain(r) for r in result.scalars().all()]

    async def update(self, tenant_id: UUID, delivery_id: UUID, data: dict) -> MilkDelivery | None:
        stmt = (
            update(MilkDeliveryORM)
            .where(MilkDeliveryORM.tenant_id == tenant_id, MilkDeliveryORM.id == delivery_id)
            .values(**data)
            .returning(MilkDeliveryORM)
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def delete(self, tenant_id: UUID, delivery_id: UUID) -> bool:
        stmt = (
            update(MilkDeliveryORM)
            .where(MilkDeliveryORM.tenant_id == tenant_id, MilkDeliveryORM.id == delivery_id)
            .values(deleted_at=func.now())
        )
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def summarize(
        self,
        tenant_id: UUID,
        *,
        date_from: date,
        date_to: date,
        buyer_id: UUID | None,
        period: str,
    ) -> list[dict]:
        # period: 'daily'|'weekly'|'monthly'
        group_expr = {
            "daily": text("date"),
            "weekly": text("strftime('%Y-%W', date)"),
            "monthly": text("strftime('%Y-%m', date)"),
        }[period]
        conds = [
            MilkDeliveryORM.tenant_id == tenant_id,
            MilkDeliveryORM.date >= date_from,
            MilkDeliveryORM.date <= date_to,
            MilkDeliveryORM.deleted_at.is_(None),
        ]
        if buyer_id is not None:
            conds.append(MilkDeliveryORM.buyer_id == buyer_id)
        stmt = (
            select(
                group_expr.label("period"),
                func.sum(MilkDeliveryORM.volume_l).label("total_liters"),
                func.sum(MilkDeliveryORM.amount).label("total_amount"),
            )
            .where(and_(*conds))
            .group_by(group_expr)
            .order_by(group_expr)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        return [
            {"period": r.period, "total_liters": r.total_liters, "total_amount": r.total_amount}
            for r in rows
        ]
