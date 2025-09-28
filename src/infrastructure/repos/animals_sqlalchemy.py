from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.errors import ConflictError, InfrastructureError
from src.application.interfaces.repositories.animals import AnimalRepository
from src.domain.models.animal import Animal
from src.infrastructure.db.orm.animal import AnimalORM


class AnimalsSQLAlchemyRepository(AnimalRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: AnimalORM) -> Animal:
        return Animal(
            id=orm.id,
            tenant_id=orm.tenant_id,
            tag=orm.tag,
            name=orm.name,
            breed=orm.breed,
            breed_variant=orm.breed_variant,
            breed_id=orm.breed_id,
            birth_date=orm.birth_date,
            lot=orm.lot,
            current_lot_id=orm.current_lot_id,
            status_id=orm.status_id,
            photo_url=orm.photo_url,
            deleted_at=orm.deleted_at,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            version=orm.version,
        )

    async def add(self, animal: Animal) -> Animal:
        orm = AnimalORM(
            id=animal.id,
            tenant_id=animal.tenant_id,
            tag=animal.tag,
            name=animal.name,
            breed=animal.breed,
            breed_variant=animal.breed_variant,
            breed_id=animal.breed_id,
            birth_date=animal.birth_date,
            lot=animal.lot,
            current_lot_id=animal.current_lot_id,
            status_id=animal.status_id,
            photo_url=animal.photo_url,
            deleted_at=animal.deleted_at,
            created_at=animal.created_at,
            updated_at=animal.updated_at,
            version=animal.version,
        )
        self.session.add(orm)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError("Animal tag already exists for tenant") from exc
        return self._to_domain(orm)

    async def get(self, tenant_id: UUID, animal_id: UUID) -> Animal | None:
        stmt = (
            select(AnimalORM)
            .where(AnimalORM.tenant_id == tenant_id)
            .where(AnimalORM.id == animal_id)
            .where(AnimalORM.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list(
        self,
        tenant_id: UUID,
        *,
        limit: int | None = None,
        cursor: UUID | None = None,
        is_active: bool | None = None,
        status_ids: list[UUID] | None = None,
    ) -> list[Animal] | tuple[list[Animal], UUID | None]:
        stmt = select(AnimalORM).where(AnimalORM.tenant_id == tenant_id)
        stmt = stmt.where(AnimalORM.deleted_at.is_(None))

        # Filter by status_ids if provided
        if status_ids is not None:
            stmt = stmt.where(AnimalORM.status_id.in_(status_ids))
        elif is_active is not None:
            # Legacy is_active filter - deprecated, use status_ids instead
            # For now, this will not work until all animals have status_id populated
            pass

        if cursor:
            stmt = stmt.where(AnimalORM.id > cursor)

        stmt = stmt.order_by(AnimalORM.id)

        if limit is not None:
            stmt = stmt.limit(limit + 1)
            result = await self.session.execute(stmt)
            rows = result.scalars().all()
            has_more = len(rows) > limit
            items = rows[:limit]
            next_cursor = items[-1].id if has_more else None
            return [self._to_domain(item) for item in items], next_cursor
        else:
            result = await self.session.execute(stmt)
            rows = result.scalars().all()
            return [self._to_domain(item) for item in rows]

    async def count(self, tenant_id: UUID, *, is_active: bool | None = None) -> int:
        stmt = select(func.count(AnimalORM.id)).where(AnimalORM.tenant_id == tenant_id)
        stmt = stmt.where(AnimalORM.deleted_at.is_(None))

        if is_active is not None:
            # Legacy is_active filter - deprecated, use status_ids instead
            # For now, this will not work until all animals have status_id populated
            pass

        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def update(
        self,
        tenant_id: UUID,
        animal_id: UUID,
        data: dict,
        expected_version: int,
    ) -> Animal | None:
        values = {**data, "version": expected_version + 1}
        stmt = (
            update(AnimalORM)
            .where(AnimalORM.tenant_id == tenant_id, AnimalORM.id == animal_id)
            .where(AnimalORM.version == expected_version)
            .where(AnimalORM.deleted_at.is_(None))
            .values(**values)
            .returning(AnimalORM)
        )
        try:
            result = await self.session.execute(stmt)
        except IntegrityError as exc:
            raise ConflictError("Failed to update animal due to constraint violation") from exc
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return self._to_domain(orm)

    async def delete(self, tenant_id: UUID, animal_id: UUID) -> bool:
        stmt = (
            update(AnimalORM)
            .where(AnimalORM.tenant_id == tenant_id)
            .where(AnimalORM.id == animal_id)
            .where(AnimalORM.deleted_at.is_(None))
            .values(deleted_at=func.now(), version=AnimalORM.version + 1)
            .returning(AnimalORM.id)
        )
        try:
            result = await self.session.execute(stmt)
        except IntegrityError as exc:
            raise InfrastructureError("Failed to delete animal") from exc
        return result.scalar_one_or_none() is not None

    async def count_by_breed_id_or_name(
        self, tenant_id: UUID, *, breed_id: UUID | None = None, breed_name: str | None = None
    ) -> int:
        stmt = select(func.count(AnimalORM.id)).where(AnimalORM.tenant_id == tenant_id)
        if breed_id is not None:
            stmt = stmt.where(AnimalORM.breed_id == breed_id)
        if breed_name is not None:
            stmt = stmt.where(func.lower(AnimalORM.breed) == func.lower(breed_name))
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    async def count_by_current_lot_id_or_name(
        self, tenant_id: UUID, *, lot_id: UUID | None = None, lot_name: str | None = None
    ) -> int:
        stmt = select(func.count(AnimalORM.id)).where(AnimalORM.tenant_id == tenant_id)
        if lot_id is not None:
            stmt = stmt.where(AnimalORM.current_lot_id == lot_id)
        if lot_name is not None:
            stmt = stmt.where(func.lower(AnimalORM.lot) == func.lower(lot_name))
        result = await self.session.execute(stmt)
        return result.scalar() or 0
