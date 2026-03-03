from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import asc, case, desc, func, literal_column, select
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

    async def get_reproductive_stats(
        self,
        tenant_id: UUID,
        date_from: datetime,
        date_to: datetime,
    ) -> dict:
        """Aggregate: cows inseminated, straws used, and
        status counts (based on last insemination per animal)."""
        # Cows inseminated & straws used (direct aggregation, no subquery)
        agg_stmt = (
            select(
                func.count(func.distinct(InseminationORM.animal_id)).label("cows_inseminated"),
                func.coalesce(func.sum(InseminationORM.straw_count), 0).label("straws_used"),
            )
            .where(InseminationORM.tenant_id == tenant_id)
            .where(InseminationORM.deleted_at.is_(None))
            .where(InseminationORM.service_date >= date_from)
            .where(InseminationORM.service_date <= date_to)
        )

        agg_result = await self.session.execute(agg_stmt)
        row = agg_result.one()

        # Status counts based on last insemination per animal (within date range)
        ranked = (
            select(
                InseminationORM.animal_id,
                InseminationORM.pregnancy_status,
                func.row_number()
                .over(
                    partition_by=InseminationORM.animal_id,
                    order_by=InseminationORM.service_date.desc(),
                )
                .label("rn"),
            )
            .where(InseminationORM.tenant_id == tenant_id)
            .where(InseminationORM.deleted_at.is_(None))
            .where(InseminationORM.service_date >= date_from)
            .where(InseminationORM.service_date <= date_to)
            .subquery()
        )

        status_stmt = (
            select(
                ranked.c.pregnancy_status,
                func.count().label("cnt"),
            )
            .where(ranked.c.rn == 1)
            .group_by(ranked.c.pregnancy_status)
        )

        status_result = await self.session.execute(status_stmt)
        status_counts = {r.pregnancy_status: r.cnt for r in status_result.all()}

        return {
            "cows_inseminated": row.cows_inseminated or 0,
            "straws_used": row.straws_used or 0,
            "status_counts": status_counts,
        }

    async def get_services_distribution(
        self,
        tenant_id: UUID,
        date_from: datetime,
        date_to: datetime,
    ) -> dict:
        """Count animals by number of services: 1, 2, 3+."""
        animal_counts = (
            select(
                InseminationORM.animal_id,
                func.count().label("svc_count"),
            )
            .where(InseminationORM.tenant_id == tenant_id)
            .where(InseminationORM.deleted_at.is_(None))
            .where(InseminationORM.service_date >= date_from)
            .where(InseminationORM.service_date <= date_to)
            .group_by(InseminationORM.animal_id)
            .subquery()
        )

        dist_stmt = select(
            func.sum(case((animal_counts.c.svc_count == 1, 1), else_=0)).label("one_service"),
            func.sum(case((animal_counts.c.svc_count == 2, 1), else_=0)).label("two_services"),
            func.sum(case((animal_counts.c.svc_count >= 3, 1), else_=0)).label("three_plus"),
        ).select_from(animal_counts)

        result = await self.session.execute(dist_stmt)
        r = result.one()
        return {
            "one_service": r.one_service or 0,
            "two_services": r.two_services or 0,
            "three_plus_services": r.three_plus or 0,
        }

    async def get_monthly_activity(
        self,
        tenant_id: UUID,
        date_from: datetime,
        date_to: datetime,
    ) -> list[dict]:
        """Monthly straws used and cows inseminated."""
        month_expr = func.to_char(InseminationORM.service_date, literal_column("'YYYY-MM'"))

        stmt = (
            select(
                month_expr.label("month"),
                func.coalesce(func.sum(InseminationORM.straw_count), 0).label("straws_used"),
                func.count(func.distinct(InseminationORM.animal_id)).label("cows_inseminated"),
            )
            .where(InseminationORM.tenant_id == tenant_id)
            .where(InseminationORM.deleted_at.is_(None))
            .where(InseminationORM.service_date >= date_from)
            .where(InseminationORM.service_date <= date_to)
            .group_by(month_expr)
            .order_by(month_expr)
        )

        result = await self.session.execute(stmt)
        return [
            {
                "month": r.month,
                "straws_used": r.straws_used or 0,
                "cows_inseminated": r.cows_inseminated or 0,
            }
            for r in result.all()
        ]

    async def get_monthly_trends(
        self,
        tenant_id: UUID,
        date_from: datetime,
        date_to: datetime,
    ) -> list[dict]:
        """Monthly conception rate, insemination count, and services per cow."""
        month_expr = func.to_char(InseminationORM.service_date, literal_column("'YYYY-MM'"))

        stmt = (
            select(
                month_expr.label("month"),
                func.count().label("insemination_count"),
                func.count(func.distinct(InseminationORM.animal_id)).label("distinct_animals"),
                func.sum(
                    case(
                        (InseminationORM.pregnancy_status == PregnancyStatus.CONFIRMED.value, 1),
                        else_=0,
                    )
                ).label("confirmed_count"),
                func.coalesce(func.sum(InseminationORM.straw_count), 0).label("straws_used"),
            )
            .where(InseminationORM.tenant_id == tenant_id)
            .where(InseminationORM.deleted_at.is_(None))
            .where(InseminationORM.service_date >= date_from)
            .where(InseminationORM.service_date <= date_to)
            .group_by(month_expr)
            .order_by(month_expr)
        )

        result = await self.session.execute(stmt)
        rows = []
        for r in result.all():
            straws = r.straws_used or 1
            conception_rate = round((r.confirmed_count / straws) * 100, 1) if straws else 0.0
            services_per_cow = (
                round(r.insemination_count / r.distinct_animals, 2) if r.distinct_animals else 0.0
            )
            rows.append(
                {
                    "month": r.month,
                    "conception_rate": conception_rate,
                    "insemination_count": r.insemination_count,
                    "services_per_cow": services_per_cow,
                }
            )
        return rows

    async def delete(self, insemination: Insemination) -> None:
        orm = await self.session.get(InseminationORM, insemination.id)
        if orm:
            orm.deleted_at = insemination.deleted_at
