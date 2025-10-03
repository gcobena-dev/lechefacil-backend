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
            sex=orm.sex,
            dam_id=orm.dam_id,
            sire_id=orm.sire_id,
            external_sire_code=orm.external_sire_code,
            external_sire_registry=orm.external_sire_registry,
            disposition_at=orm.disposition_at,
            disposition_reason=orm.disposition_reason,
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
            sex=animal.sex,
            dam_id=animal.dam_id,
            sire_id=animal.sire_id,
            external_sire_code=animal.external_sire_code,
            external_sire_registry=animal.external_sire_registry,
            disposition_at=animal.disposition_at,
            disposition_reason=animal.disposition_reason,
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
        offset: int | None = None,
        is_active: bool | None = None,
        status_ids: list[UUID] | None = None,
    ) -> list[Animal] | tuple[list[Animal], UUID | None]:
        stmt = select(AnimalORM).where(AnimalORM.tenant_id == tenant_id)
        stmt = stmt.where(AnimalORM.deleted_at.is_(None))

        # Filter by status_ids if provided
        if status_ids is not None:
            stmt = stmt.where(AnimalORM.status_id.in_(status_ids))
        elif is_active is not None:
            # Legacy is_active filter - implemented using status codes
            # Get inactive status IDs (SOLD, DEAD, CULLED)
            from .animal_statuses_sqlalchemy import AnimalStatusORM

            inactive_statuses_stmt = select(AnimalStatusORM.id).where(
                AnimalStatusORM.code.in_(["SOLD", "DEAD", "CULLED"])
            )
            inactive_status_result = await self.session.execute(inactive_statuses_stmt)
            inactive_status_ids = [row[0] for row in inactive_status_result.fetchall()]

            if is_active:
                # Include animals that are NOT in inactive statuses (or have null status_id)
                if inactive_status_ids:
                    stmt = stmt.where(
                        (AnimalORM.status_id.is_(None))
                        | (~AnimalORM.status_id.in_(inactive_status_ids))
                    )
            else:
                # Only include animals with inactive statuses
                if inactive_status_ids:
                    stmt = stmt.where(AnimalORM.status_id.in_(inactive_status_ids))

        stmt = stmt.order_by(AnimalORM.id)

        # Use offset-based pagination if offset is provided
        if offset is not None:
            stmt = stmt.offset(offset)
            if limit is not None:
                stmt = stmt.limit(limit)
            result = await self.session.execute(stmt)
            rows = result.scalars().all()
            # For offset pagination, return items and None cursor
            return [self._to_domain(item) for item in rows], None
        # Use cursor-based pagination otherwise
        elif cursor:
            stmt = stmt.where(AnimalORM.id > cursor)
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
                return [self._to_domain(item) for item in rows], None
        else:
            # No pagination specified
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

    async def count(
        self,
        tenant_id: UUID,
        *,
        is_active: bool | None = None,
        status_ids: list[UUID] | None = None,
    ) -> int:
        stmt = select(func.count(AnimalORM.id)).where(AnimalORM.tenant_id == tenant_id)
        stmt = stmt.where(AnimalORM.deleted_at.is_(None))

        # Filter by status_ids if provided
        if status_ids is not None:
            stmt = stmt.where(AnimalORM.status_id.in_(status_ids))
        elif is_active is not None:
            # Legacy is_active filter - implemented using status codes
            # Get inactive status IDs (SOLD, DEAD, CULLED)
            from .animal_statuses_sqlalchemy import AnimalStatusORM

            inactive_statuses_stmt = select(AnimalStatusORM.id).where(
                AnimalStatusORM.code.in_(["SOLD", "DEAD", "CULLED"])
            )
            inactive_status_result = await self.session.execute(inactive_statuses_stmt)
            inactive_status_ids = [row[0] for row in inactive_status_result.fetchall()]

            if is_active:
                # Exclude animals with inactive statuses
                # Also include animals with null status_id (treated as active)
                stmt = stmt.where(
                    (AnimalORM.status_id.is_(None))
                    | (~AnimalORM.status_id.in_(inactive_status_ids))
                )
            else:
                # Only include animals with inactive statuses
                if inactive_status_ids:
                    stmt = stmt.where(AnimalORM.status_id.in_(inactive_status_ids))

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
