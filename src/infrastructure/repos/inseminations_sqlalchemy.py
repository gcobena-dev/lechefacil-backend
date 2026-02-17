from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.insemination import Insemination, PregnancyStatus
from src.infrastructure.db.orm.animal import AnimalORM
from src.infrastructure.db.orm.insemination import InseminationORM
from src.infrastructure.db.orm.sire_catalog import SireCatalogORM


class InseminationsSQLAlchemyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: InseminationORM) -> Insemination:
        return Insemination(
            id=orm.id,
            tenant_id=orm.tenant_id,
            animal_id=orm.animal_id,
            sire_catalog_id=orm.sire_catalog_id,
            semen_inventory_id=orm.semen_inventory_id,
            service_event_id=orm.service_event_id,
            service_date=orm.service_date,
            method=orm.method,
            technician=orm.technician,
            straw_count=orm.straw_count,
            heat_detected=orm.heat_detected,
            protocol=orm.protocol,
            pregnancy_status=orm.pregnancy_status,
            pregnancy_check_date=orm.pregnancy_check_date,
            pregnancy_checked_by=orm.pregnancy_checked_by,
            expected_calving_date=orm.expected_calving_date,
            calving_event_id=orm.calving_event_id,
            notes=orm.notes,
            deleted_at=orm.deleted_at,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            version=orm.version,
        )

    async def add(self, insemination: Insemination) -> Insemination:
        orm = InseminationORM(
            id=insemination.id,
            tenant_id=insemination.tenant_id,
            animal_id=insemination.animal_id,
            sire_catalog_id=insemination.sire_catalog_id,
            semen_inventory_id=insemination.semen_inventory_id,
            service_event_id=insemination.service_event_id,
            service_date=insemination.service_date,
            method=insemination.method,
            technician=insemination.technician,
            straw_count=insemination.straw_count,
            heat_detected=insemination.heat_detected,
            protocol=insemination.protocol,
            pregnancy_status=insemination.pregnancy_status,
            pregnancy_check_date=insemination.pregnancy_check_date,
            pregnancy_checked_by=insemination.pregnancy_checked_by,
            expected_calving_date=insemination.expected_calving_date,
            calving_event_id=insemination.calving_event_id,
            notes=insemination.notes,
            created_at=insemination.created_at,
            updated_at=insemination.updated_at,
            version=insemination.version,
        )
        self.session.add(orm)
        await self.session.flush()
        return self._to_domain(orm)

    async def update(self, insemination: Insemination) -> Insemination:
        orm = await self.session.get(InseminationORM, insemination.id)
        if not orm:
            raise ValueError(f"Insemination {insemination.id} not found")
        orm.sire_catalog_id = insemination.sire_catalog_id
        orm.semen_inventory_id = insemination.semen_inventory_id
        orm.service_event_id = insemination.service_event_id
        orm.service_date = insemination.service_date
        orm.method = insemination.method
        orm.technician = insemination.technician
        orm.straw_count = insemination.straw_count
        orm.heat_detected = insemination.heat_detected
        orm.protocol = insemination.protocol
        orm.pregnancy_status = insemination.pregnancy_status
        orm.pregnancy_check_date = insemination.pregnancy_check_date
        orm.pregnancy_checked_by = insemination.pregnancy_checked_by
        orm.expected_calving_date = insemination.expected_calving_date
        orm.calving_event_id = insemination.calving_event_id
        orm.notes = insemination.notes
        orm.updated_at = insemination.updated_at
        orm.version = insemination.version
        await self.session.flush()
        return self._to_domain(orm)

    async def get(self, tenant_id: UUID, insemination_id: UUID) -> Insemination | None:
        stmt = (
            select(InseminationORM)
            .where(InseminationORM.tenant_id == tenant_id)
            .where(InseminationORM.id == insemination_id)
            .where(InseminationORM.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    def _apply_filters(
        self, stmt, tenant_id, animal_id, sire_catalog_id, pregnancy_status, date_from, date_to
    ):
        stmt = stmt.where(InseminationORM.tenant_id == tenant_id)
        stmt = stmt.where(InseminationORM.deleted_at.is_(None))
        if animal_id:
            stmt = stmt.where(InseminationORM.animal_id == animal_id)
        if sire_catalog_id:
            stmt = stmt.where(InseminationORM.sire_catalog_id == sire_catalog_id)
        if pregnancy_status:
            stmt = stmt.where(InseminationORM.pregnancy_status == pregnancy_status)
        if date_from:
            stmt = stmt.where(InseminationORM.service_date >= date_from)
        if date_to:
            stmt = stmt.where(InseminationORM.service_date <= date_to)
        return stmt

    async def list(
        self,
        tenant_id: UUID,
        animal_id: UUID | None = None,
        sire_catalog_id: UUID | None = None,
        pregnancy_status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int | None = None,
        offset: int = 0,
        sort_by: str | None = None,
        sort_dir: str | None = None,
    ) -> list[Insemination]:
        stmt = select(InseminationORM)
        stmt = self._apply_filters(
            stmt, tenant_id, animal_id, sire_catalog_id, pregnancy_status, date_from, date_to
        )

        # Order handling
        order_direction = (sort_dir or "desc").lower()
        direction_fn = asc if order_direction != "desc" else desc
        sort_key = (sort_by or "service_date").lower()

        if sort_key == "animal":
            stmt = stmt.join(AnimalORM, AnimalORM.id == InseminationORM.animal_id, isouter=True)
            stmt = stmt.order_by(direction_fn(AnimalORM.tag))
        elif sort_key == "sire":
            stmt = stmt.join(
                SireCatalogORM, SireCatalogORM.id == InseminationORM.sire_catalog_id, isouter=True
            )
            stmt = stmt.order_by(direction_fn(SireCatalogORM.name))
        elif sort_key == "method":
            stmt = stmt.order_by(direction_fn(InseminationORM.method))
        elif sort_key == "technician":
            stmt = stmt.order_by(direction_fn(InseminationORM.technician))
        elif sort_key == "pregnancy_status":
            stmt = stmt.order_by(direction_fn(InseminationORM.pregnancy_status))
        elif sort_key == "expected_calving_date":
            stmt = stmt.order_by(direction_fn(InseminationORM.expected_calving_date))
        else:
            # default: service_date
            stmt = stmt.order_by(direction_fn(InseminationORM.service_date))

        stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def count(
        self,
        tenant_id: UUID,
        animal_id: UUID | None = None,
        sire_catalog_id: UUID | None = None,
        pregnancy_status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(InseminationORM)
        stmt = self._apply_filters(
            stmt, tenant_id, animal_id, sire_catalog_id, pregnancy_status, date_from, date_to
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def get_pending_checks(
        self,
        tenant_id: UUID,
        min_days: int = 35,
        max_days: int = 50,
    ) -> list[Insemination]:
        now = datetime.now(timezone.utc)
        min_date = now - timedelta(days=max_days)
        max_date = now - timedelta(days=min_days)
        stmt = (
            select(InseminationORM)
            .where(InseminationORM.tenant_id == tenant_id)
            .where(InseminationORM.pregnancy_status == PregnancyStatus.PENDING.value)
            .where(InseminationORM.service_date >= min_date)
            .where(InseminationORM.service_date <= max_date)
            .where(InseminationORM.deleted_at.is_(None))
            .order_by(InseminationORM.service_date)
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_latest_confirmed(
        self,
        tenant_id: UUID,
        animal_id: UUID,
    ) -> Insemination | None:
        stmt = (
            select(InseminationORM)
            .where(InseminationORM.tenant_id == tenant_id)
            .where(InseminationORM.animal_id == animal_id)
            .where(InseminationORM.pregnancy_status == PregnancyStatus.CONFIRMED.value)
            .where(InseminationORM.calving_event_id.is_(None))
            .where(InseminationORM.deleted_at.is_(None))
            .order_by(InseminationORM.service_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def count_by_sire(
        self,
        tenant_id: UUID,
        sire_catalog_id: UUID,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(InseminationORM)
            .where(InseminationORM.tenant_id == tenant_id)
            .where(InseminationORM.sire_catalog_id == sire_catalog_id)
            .where(InseminationORM.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def count_confirmed_by_sire(
        self,
        tenant_id: UUID,
        sire_catalog_id: UUID,
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(InseminationORM)
            .where(InseminationORM.tenant_id == tenant_id)
            .where(InseminationORM.sire_catalog_id == sire_catalog_id)
            .where(InseminationORM.pregnancy_status == PregnancyStatus.CONFIRMED.value)
            .where(InseminationORM.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def delete(self, insemination: Insemination) -> None:
        orm = await self.session.get(InseminationORM, insemination.id)
        if orm:
            orm.deleted_at = insemination.deleted_at
