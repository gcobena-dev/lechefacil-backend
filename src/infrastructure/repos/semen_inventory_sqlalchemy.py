from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.semen_inventory import SemenInventory
from src.infrastructure.db.orm.semen_inventory import SemenInventoryORM
from src.infrastructure.db.orm.sire_catalog import SireCatalogORM


class SemenInventorySQLAlchemyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: SemenInventoryORM) -> SemenInventory:
        return SemenInventory(
            id=orm.id,
            tenant_id=orm.tenant_id,
            sire_catalog_id=orm.sire_catalog_id,
            batch_code=orm.batch_code,
            tank_id=orm.tank_id,
            canister_position=orm.canister_position,
            initial_quantity=orm.initial_quantity,
            current_quantity=orm.current_quantity,
            supplier=orm.supplier,
            cost_per_straw=orm.cost_per_straw,
            currency=orm.currency,
            purchase_date=orm.purchase_date,
            expiry_date=orm.expiry_date,
            notes=orm.notes,
            deleted_at=orm.deleted_at,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            version=orm.version,
        )

    async def add(self, stock: SemenInventory) -> SemenInventory:
        orm = SemenInventoryORM(
            id=stock.id,
            tenant_id=stock.tenant_id,
            sire_catalog_id=stock.sire_catalog_id,
            batch_code=stock.batch_code,
            tank_id=stock.tank_id,
            canister_position=stock.canister_position,
            initial_quantity=stock.initial_quantity,
            current_quantity=stock.current_quantity,
            supplier=stock.supplier,
            cost_per_straw=stock.cost_per_straw,
            currency=stock.currency,
            purchase_date=stock.purchase_date,
            expiry_date=stock.expiry_date,
            notes=stock.notes,
            created_at=stock.created_at,
            updated_at=stock.updated_at,
            version=stock.version,
        )
        self.session.add(orm)
        await self.session.flush()
        return self._to_domain(orm)

    async def update(self, stock: SemenInventory) -> SemenInventory:
        orm = await self.session.get(SemenInventoryORM, stock.id)
        if not orm:
            raise ValueError(f"SemenInventory {stock.id} not found")
        orm.batch_code = stock.batch_code
        orm.tank_id = stock.tank_id
        orm.canister_position = stock.canister_position
        orm.initial_quantity = stock.initial_quantity
        orm.current_quantity = stock.current_quantity
        orm.supplier = stock.supplier
        orm.cost_per_straw = stock.cost_per_straw
        orm.currency = stock.currency
        orm.purchase_date = stock.purchase_date
        orm.expiry_date = stock.expiry_date
        orm.notes = stock.notes
        orm.updated_at = stock.updated_at
        orm.version = stock.version
        await self.session.flush()
        return self._to_domain(orm)

    async def get(self, tenant_id: UUID, stock_id: UUID) -> SemenInventory | None:
        stmt = (
            select(SemenInventoryORM)
            .where(SemenInventoryORM.tenant_id == tenant_id)
            .where(SemenInventoryORM.id == stock_id)
            .where(SemenInventoryORM.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_by_sire(
        self,
        tenant_id: UUID,
        sire_catalog_id: UUID,
        in_stock_only: bool = False,
    ) -> list[SemenInventory]:
        stmt = (
            select(SemenInventoryORM)
            .where(SemenInventoryORM.tenant_id == tenant_id)
            .where(SemenInventoryORM.sire_catalog_id == sire_catalog_id)
            .where(SemenInventoryORM.deleted_at.is_(None))
            .order_by(SemenInventoryORM.purchase_date.desc().nullslast())
        )
        if in_stock_only:
            stmt = stmt.where(SemenInventoryORM.current_quantity > 0)
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def list(
        self,
        tenant_id: UUID,
        in_stock_only: bool = False,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[SemenInventory]:
        stmt = (
            select(SemenInventoryORM)
            .where(SemenInventoryORM.tenant_id == tenant_id)
            .where(SemenInventoryORM.deleted_at.is_(None))
            .order_by(SemenInventoryORM.created_at.desc())
            .offset(offset)
        )
        if in_stock_only:
            stmt = stmt.where(SemenInventoryORM.current_quantity > 0)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def count(
        self,
        tenant_id: UUID,
        in_stock_only: bool = False,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(SemenInventoryORM)
            .where(SemenInventoryORM.tenant_id == tenant_id)
            .where(SemenInventoryORM.deleted_at.is_(None))
        )
        if in_stock_only:
            stmt = stmt.where(SemenInventoryORM.current_quantity > 0)
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def count_distinct_breeds(
        self,
        tenant_id: UUID,
        in_stock_only: bool = True,
    ) -> int:
        stmt = (
            select(func.count(func.distinct(SireCatalogORM.breed_id)))
            .select_from(SemenInventoryORM)
            .join(SireCatalogORM, SireCatalogORM.id == SemenInventoryORM.sire_catalog_id)
            .where(SemenInventoryORM.tenant_id == tenant_id)
            .where(SemenInventoryORM.deleted_at.is_(None))
            .where(SireCatalogORM.breed_id.is_not(None))
        )
        if in_stock_only:
            stmt = stmt.where(SemenInventoryORM.current_quantity > 0)
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def _distinct_values(
        self, tenant_id: UUID, column, limit: int
    ) -> list[str]:
        stmt = (
            select(column)
            .where(SemenInventoryORM.tenant_id == tenant_id)
            .where(SemenInventoryORM.deleted_at.is_(None))
            .where(column.isnot(None))
            .where(column != "")
            .group_by(column)
            .order_by(func.count().desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all()]

    async def get_autocomplete_values(
        self, tenant_id: UUID, limit: int = 50
    ) -> dict[str, list[str]]:
        return {
            "suppliers": await self._distinct_values(
                tenant_id, SemenInventoryORM.supplier, limit
            ),
            "batch_codes": await self._distinct_values(
                tenant_id, SemenInventoryORM.batch_code, limit
            ),
            "tank_ids": await self._distinct_values(
                tenant_id, SemenInventoryORM.tank_id, limit
            ),
            "canister_positions": await self._distinct_values(
                tenant_id, SemenInventoryORM.canister_position, limit
            ),
        }

    async def aggregate_stock_by_sire(
        self,
        tenant_id: UUID,
    ) -> dict[UUID, int]:
        """Sum of current_quantity grouped by sire_catalog_id."""
        stmt = (
            select(
                SemenInventoryORM.sire_catalog_id.label("sire_id"),
                func.coalesce(
                    func.sum(SemenInventoryORM.current_quantity), 0
                ).label("straws_in_stock"),
            )
            .where(SemenInventoryORM.tenant_id == tenant_id)
            .where(SemenInventoryORM.deleted_at.is_(None))
            .group_by(SemenInventoryORM.sire_catalog_id)
        )
        result = await self.session.execute(stmt)
        return {r.sire_id: int(r.straws_in_stock or 0) for r in result.all()}

    async def delete(self, stock: SemenInventory) -> None:
        orm = await self.session.get(SemenInventoryORM, stock.id)
        if orm:
            orm.deleted_at = stock.deleted_at
