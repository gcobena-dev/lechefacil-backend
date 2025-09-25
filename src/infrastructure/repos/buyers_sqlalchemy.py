from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.errors import ConflictError
from src.application.interfaces.repositories.buyers import BuyersRepository
from src.domain.models.buyer import Buyer
from src.infrastructure.db.orm.buyer import BuyerORM


class BuyersSQLAlchemyRepository(BuyersRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: BuyerORM) -> Buyer:
        return Buyer(
            id=orm.id,
            tenant_id=orm.tenant_id,
            name=orm.name,
            code=orm.code,
            contact=orm.contact,
            is_active=orm.is_active,
            deleted_at=orm.deleted_at,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            version=orm.version,
        )

    async def add(self, buyer: Buyer) -> Buyer:
        orm = BuyerORM(
            id=buyer.id,
            tenant_id=buyer.tenant_id,
            name=buyer.name,
            code=buyer.code,
            contact=buyer.contact,
            is_active=buyer.is_active,
            deleted_at=buyer.deleted_at,
            created_at=buyer.created_at,
            updated_at=buyer.updated_at,
            version=buyer.version,
        )
        self.session.add(orm)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError("Buyer name already exists") from exc
        return self._to_domain(orm)

    async def list(self, tenant_id: UUID) -> list[Buyer]:
        stmt = select(BuyerORM).where(
            BuyerORM.tenant_id == tenant_id, BuyerORM.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(r) for r in result.scalars().all()]

    async def get(self, tenant_id: UUID, buyer_id: UUID) -> Buyer | None:
        stmt = select(BuyerORM).where(
            BuyerORM.tenant_id == tenant_id, BuyerORM.id == buyer_id, BuyerORM.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def set_active(self, tenant_id: UUID, buyer_id: UUID, is_active: bool) -> None:
        stmt = (
            update(BuyerORM)
            .where(BuyerORM.tenant_id == tenant_id, BuyerORM.id == buyer_id)
            .values(is_active=is_active)
        )
        await self.session.execute(stmt)
