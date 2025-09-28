from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.errors import ConflictError, InfrastructureError
from src.domain.models.lot import Lot
from src.domain.ports.lots_repo import LotsRepo
from src.infrastructure.db.orm.lot import LotORM


class LotsSQLAlchemyRepository(LotsRepo):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: LotORM) -> Lot:
        return Lot(
            id=orm.id,
            tenant_id=orm.tenant_id,
            name=orm.name,
            active=orm.active,
            notes=orm.notes,
            created_at=orm.created_at,
        )

    async def add(self, lot: Lot) -> Lot:
        orm = LotORM(
            id=lot.id,
            tenant_id=lot.tenant_id,
            name=lot.name,
            active=lot.active,
            notes=lot.notes,
        )
        self.session.add(orm)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError("Failed to create lot") from exc
        return self._to_domain(orm)

    async def get(self, tenant_id: UUID, lot_id: UUID) -> Lot | None:
        stmt = select(LotORM).where(LotORM.tenant_id == tenant_id, LotORM.id == lot_id)
        res = await self.session.execute(stmt)
        orm = res.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def find_by_name(self, tenant_id: UUID, name: str) -> Lot | None:
        stmt = select(LotORM).where(LotORM.tenant_id == tenant_id, LotORM.name.ilike(name))
        res = await self.session.execute(stmt)
        orm = res.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_for_tenant(self, tenant_id: UUID, *, active: bool | None = None) -> list[Lot]:
        stmt = select(LotORM).where(LotORM.tenant_id == tenant_id)
        if active is not None:
            stmt = stmt.where(LotORM.active.is_(active))
        res = await self.session.execute(stmt)
        items = res.scalars().all()
        return [self._to_domain(x) for x in items]

    async def update(self, tenant_id: UUID, lot_id: UUID, data: dict) -> Lot | None:
        stmt = (
            update(LotORM)
            .where(LotORM.tenant_id == tenant_id, LotORM.id == lot_id)
            .values(**data)
            .returning(LotORM)
        )
        try:
            res = await self.session.execute(stmt)
        except IntegrityError as exc:
            raise InfrastructureError("Failed to update lot") from exc
        orm = res.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def soft_delete(self, tenant_id: UUID, lot_id: UUID) -> bool:
        stmt = (
            update(LotORM)
            .where(LotORM.tenant_id == tenant_id, LotORM.id == lot_id)
            .values(active=False)
            .returning(LotORM.id)
        )
        try:
            res = await self.session.execute(stmt)
        except IntegrityError as exc:
            raise InfrastructureError("Failed to delete lot") from exc
        return res.scalar_one_or_none() is not None
