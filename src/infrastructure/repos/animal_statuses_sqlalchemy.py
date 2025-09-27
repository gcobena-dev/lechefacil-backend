from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.animal_status import AnimalStatus
from src.domain.ports.animal_statuses_repo import AnimalStatusesRepo
from src.infrastructure.db.orm.animal_status import AnimalStatusORM


class AnimalStatusesSqlAlchemyRepo(AnimalStatusesRepo):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, status: AnimalStatus) -> AnimalStatus:
        orm = AnimalStatusORM(
            id=status.id,
            tenant_id=status.tenant_id,
            code=status.code,
            translations=status.translations,
            is_system_default=status.is_system_default,
            created_at=status.created_at,
        )
        self._session.add(orm)
        await self._session.flush()
        return status

    async def get_by_id(self, status_id: UUID) -> AnimalStatus | None:
        result = await self._session.execute(
            select(AnimalStatusORM).where(AnimalStatusORM.id == status_id)
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_code(self, tenant_id: UUID | None, code: str) -> AnimalStatus | None:
        # When tenant_id is provided, we want either the
        # tenant-specific row or the system default (tenant_id IS NULL)
        if tenant_id is None:
            stmt = (
                select(AnimalStatusORM)
                .where(AnimalStatusORM.code == code)
                .where(AnimalStatusORM.tenant_id.is_(None))
                .limit(1)
            )
        else:
            from sqlalchemy import or_

            stmt = (
                select(AnimalStatusORM)
                .where(AnimalStatusORM.code == code)
                .where(
                    or_(
                        AnimalStatusORM.tenant_id == tenant_id,
                        AnimalStatusORM.tenant_id.is_(None),
                    )
                )
                # Prefer tenant-specific over system default
                .order_by(AnimalStatusORM.tenant_id.desc().nulls_last())
                .limit(1)
            )

        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_for_tenant(self, tenant_id: UUID) -> list[AnimalStatus]:
        from sqlalchemy import or_

        result = await self._session.execute(
            select(AnimalStatusORM)
            .where(or_(AnimalStatusORM.tenant_id == tenant_id, AnimalStatusORM.tenant_id.is_(None)))
            .order_by(AnimalStatusORM.is_system_default.desc(), AnimalStatusORM.code)
        )
        return [self._to_domain(orm) for orm in result.scalars().all()]

    def _to_domain(self, orm: AnimalStatusORM) -> AnimalStatus:
        return AnimalStatus(
            id=orm.id,
            tenant_id=orm.tenant_id,
            code=orm.code,
            translations=orm.translations,
            is_system_default=orm.is_system_default,
            created_at=orm.created_at,
        )
