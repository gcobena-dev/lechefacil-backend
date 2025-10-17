from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.health_record import HealthRecord
from src.infrastructure.db.orm.health_record import HealthRecordORM


class HealthRecordsSQLAlchemyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: HealthRecordORM) -> HealthRecord:
        return HealthRecord(
            id=orm.id,
            tenant_id=orm.tenant_id,
            animal_id=orm.animal_id,
            event_type=orm.event_type,
            occurred_at=orm.occurred_at,
            veterinarian=orm.veterinarian,
            cost=orm.cost,
            notes=orm.notes,
            vaccine_name=orm.vaccine_name,
            next_dose_date=orm.next_dose_date,
            medication=orm.medication,
            duration_days=orm.duration_days,
            withdrawal_days=orm.withdrawal_days,
            withdrawal_until=orm.withdrawal_until,
            deleted_at=orm.deleted_at,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
            version=orm.version,
        )

    def _to_orm(self, record: HealthRecord) -> HealthRecordORM:
        return HealthRecordORM(
            id=record.id,
            tenant_id=record.tenant_id,
            animal_id=record.animal_id,
            event_type=record.event_type,
            occurred_at=record.occurred_at,
            veterinarian=record.veterinarian,
            cost=record.cost,
            notes=record.notes,
            vaccine_name=record.vaccine_name,
            next_dose_date=record.next_dose_date,
            medication=record.medication,
            duration_days=record.duration_days,
            withdrawal_days=record.withdrawal_days,
            withdrawal_until=record.withdrawal_until,
            deleted_at=record.deleted_at,
            created_at=record.created_at,
            updated_at=record.updated_at,
            version=record.version,
        )

    async def add(self, record: HealthRecord) -> HealthRecord:
        orm = self._to_orm(record)
        self.session.add(orm)
        await self.session.flush()
        return self._to_domain(orm)

    async def update(self, record: HealthRecord) -> HealthRecord:
        orm = await self.session.get(HealthRecordORM, record.id)
        if not orm:
            raise ValueError(f"HealthRecord {record.id} not found")

        orm.event_type = record.event_type
        orm.occurred_at = record.occurred_at
        orm.veterinarian = record.veterinarian
        orm.cost = record.cost
        orm.notes = record.notes
        orm.vaccine_name = record.vaccine_name
        orm.next_dose_date = record.next_dose_date
        orm.medication = record.medication
        orm.duration_days = record.duration_days
        orm.withdrawal_days = record.withdrawal_days
        orm.withdrawal_until = record.withdrawal_until
        orm.updated_at = record.updated_at
        orm.version = record.version

        await self.session.flush()
        return self._to_domain(orm)

    async def get(self, tenant_id: UUID, record_id: UUID) -> HealthRecord | None:
        stmt = (
            select(HealthRecordORM)
            .where(HealthRecordORM.tenant_id == tenant_id)
            .where(HealthRecordORM.id == record_id)
            .where(HealthRecordORM.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_by_animal(
        self, tenant_id: UUID, animal_id: UUID, limit: int | None = None, offset: int = 0
    ) -> list[HealthRecord]:
        stmt = (
            select(HealthRecordORM)
            .where(HealthRecordORM.tenant_id == tenant_id)
            .where(HealthRecordORM.animal_id == animal_id)
            .where(HealthRecordORM.deleted_at.is_(None))
            .order_by(HealthRecordORM.occurred_at.desc())
            .offset(offset)
        )
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def count_by_animal(self, tenant_id: UUID, animal_id: UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(HealthRecordORM)
            .where(HealthRecordORM.tenant_id == tenant_id)
            .where(HealthRecordORM.animal_id == animal_id)
            .where(HealthRecordORM.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        count = result.scalar_one()
        return int(count or 0)

    async def delete(self, record: HealthRecord) -> None:
        """Soft delete"""
        orm = await self.session.get(HealthRecordORM, record.id)
        if orm:
            orm.deleted_at = record.deleted_at

    async def get_upcoming_vaccinations(
        self, tenant_id: UUID, days_ahead: int = 7
    ) -> list[HealthRecord]:
        """Get vaccinations with next_dose_date in the next N days"""
        from datetime import timedelta

        today = date.today()
        future_date = today + timedelta(days=days_ahead)

        stmt = (
            select(HealthRecordORM)
            .where(HealthRecordORM.tenant_id == tenant_id)
            .where(HealthRecordORM.event_type == "VACCINATION")
            .where(HealthRecordORM.next_dose_date.is_not(None))
            .where(HealthRecordORM.next_dose_date >= today)
            .where(HealthRecordORM.next_dose_date <= future_date)
            .where(HealthRecordORM.deleted_at.is_(None))
            .order_by(HealthRecordORM.next_dose_date)
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def get_active_withdrawals(self, tenant_id: UUID) -> list[HealthRecord]:
        """Get treatments with active withdrawal periods"""
        today = date.today()

        stmt = (
            select(HealthRecordORM)
            .where(HealthRecordORM.tenant_id == tenant_id)
            .where(HealthRecordORM.event_type == "TREATMENT")
            .where(HealthRecordORM.withdrawal_until.is_not(None))
            .where(HealthRecordORM.withdrawal_until >= today)
            .where(HealthRecordORM.deleted_at.is_(None))
            .order_by(HealthRecordORM.withdrawal_until)
        )
        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]
