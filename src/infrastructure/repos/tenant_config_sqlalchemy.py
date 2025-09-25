from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories.tenant_config import TenantConfigRepository
from src.domain.models.tenant_config import TenantConfig
from src.infrastructure.db.orm.tenant_config import TenantConfigORM


class TenantConfigSQLAlchemyRepository(TenantConfigRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: TenantConfigORM) -> TenantConfig:
        return TenantConfig(
            tenant_id=orm.tenant_id,
            default_buyer_id=orm.default_buyer_id,
            default_density=orm.default_density,
            default_delivery_input_unit=orm.default_delivery_input_unit,
            default_production_input_unit=orm.default_production_input_unit,
            default_currency=orm.default_currency,
            default_price_per_l=orm.default_price_per_l,
            updated_at=orm.updated_at,
        )

    async def get(self, tenant_id: UUID) -> TenantConfig | None:
        result = await self.session.execute(
            select(TenantConfigORM).where(TenantConfigORM.tenant_id == tenant_id)
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def upsert(self, config: TenantConfig) -> TenantConfig:
        orm = await self.session.get(TenantConfigORM, config.tenant_id)
        if orm is None:
            orm = TenantConfigORM(
                tenant_id=config.tenant_id,
                default_buyer_id=config.default_buyer_id,
                default_density=config.default_density,
                default_delivery_input_unit=config.default_delivery_input_unit,
                default_production_input_unit=config.default_production_input_unit,
                default_currency=config.default_currency,
                default_price_per_l=config.default_price_per_l,
            )
            self.session.add(orm)
            await self.session.flush()
            return self._to_domain(orm)
        # Update existing fields from domain in case of explicit upsert usage
        orm.default_buyer_id = config.default_buyer_id
        orm.default_density = config.default_density
        orm.default_delivery_input_unit = config.default_delivery_input_unit
        orm.default_production_input_unit = config.default_production_input_unit
        orm.default_currency = config.default_currency
        orm.default_price_per_l = config.default_price_per_l
        await self.session.flush()
        return self._to_domain(orm)

    async def update(self, tenant_id: UUID, data: dict) -> TenantConfig | None:
        stmt = (
            update(TenantConfigORM)
            .where(TenantConfigORM.tenant_id == tenant_id)
            .values(**data)
            .returning(TenantConfigORM)
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None
