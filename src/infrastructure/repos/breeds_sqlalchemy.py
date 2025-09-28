from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.errors import ConflictError, InfrastructureError
from src.domain.models.breed import Breed
from src.domain.ports.breeds_repo import BreedsRepo
from src.infrastructure.db.orm.breed import BreedORM


class BreedsSQLAlchemyRepository(BreedsRepo):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: BreedORM) -> Breed:
        return Breed(
            id=orm.id,
            tenant_id=orm.tenant_id,
            name=orm.name,
            code=orm.code,
            is_system_default=orm.is_system_default,
            active=orm.active,
            metadata=orm.meta,
            created_at=orm.created_at,
        )

    async def add(self, breed: Breed) -> Breed:
        orm = BreedORM(
            id=breed.id,
            tenant_id=breed.tenant_id,
            name=breed.name,
            code=breed.code,
            is_system_default=breed.is_system_default,
            active=breed.active,
            meta=breed.metadata,
        )
        self.session.add(orm)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError("Failed to create breed") from exc
        return self._to_domain(orm)

    async def get(self, tenant_id: UUID, breed_id: UUID) -> Breed | None:
        stmt = select(BreedORM).where(
            or_(BreedORM.tenant_id == tenant_id, BreedORM.tenant_id.is_(None)),
            BreedORM.id == breed_id,
        )
        res = await self.session.execute(stmt)
        orm = res.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_any(self, breed_id: UUID) -> Breed | None:
        stmt = select(BreedORM).where(BreedORM.id == breed_id)
        res = await self.session.execute(stmt)
        orm = res.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def find_by_name(self, tenant_id: UUID, name: str) -> Breed | None:
        stmt = select(BreedORM).where(
            and_(
                or_(BreedORM.tenant_id == tenant_id, BreedORM.tenant_id.is_(None)),
                BreedORM.name.ilike(name),
            )
        )
        res = await self.session.execute(stmt)
        orm = res.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_for_tenant(self, tenant_id: UUID, *, active: bool | None = None) -> list[Breed]:
        stmt = select(BreedORM).where(
            or_(BreedORM.tenant_id == tenant_id, BreedORM.tenant_id.is_(None))
        )
        if active is not None:
            stmt = stmt.where(BreedORM.active.is_(active))
        res = await self.session.execute(stmt)
        items = res.scalars().all()
        return [self._to_domain(x) for x in items]

    async def update(self, tenant_id: UUID, breed_id: UUID, data: dict) -> Breed | None:
        stmt = (
            update(BreedORM)
            .where(BreedORM.id == breed_id, BreedORM.tenant_id == tenant_id)
            .values(**data)
            .returning(BreedORM)
        )
        try:
            res = await self.session.execute(stmt)
        except IntegrityError as exc:
            raise InfrastructureError("Failed to update breed") from exc
        orm = res.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def soft_delete(self, tenant_id: UUID, breed_id: UUID) -> bool:
        stmt = (
            update(BreedORM)
            .where(BreedORM.id == breed_id, BreedORM.tenant_id == tenant_id)
            .values(active=False)
            .returning(BreedORM.id)
        )
        try:
            res = await self.session.execute(stmt)
        except IntegrityError as exc:
            raise InfrastructureError("Failed to delete breed") from exc
        return res.scalar_one_or_none() is not None
