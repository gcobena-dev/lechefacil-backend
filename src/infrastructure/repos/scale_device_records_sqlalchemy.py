from __future__ import annotations

from uuid import UUID

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.scale_device_record import ScaleDeviceRecord
from src.infrastructure.db.orm.scale_device_record import ScaleDeviceRecordORM


class ScaleDeviceRecordsSQLAlchemyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: ScaleDeviceRecordORM) -> ScaleDeviceRecord:
        return ScaleDeviceRecord(
            id=orm.id,
            tenant_id=orm.tenant_id,
            device_id=orm.device_id,
            device_record_id=orm.device_record_id,
            codigo=orm.codigo,
            peso=orm.peso,
            fecha=orm.fecha,
            hora=orm.hora,
            turno=orm.turno,
            status=orm.status,
            matched_animal_id=orm.matched_animal_id,
            milk_production_id=orm.milk_production_id,
            batch_id=orm.batch_id,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    async def add_batch(self, records: list[ScaleDeviceRecord]) -> list[ScaleDeviceRecord]:
        orms = []
        for rec in records:
            orm = ScaleDeviceRecordORM(
                id=rec.id,
                tenant_id=rec.tenant_id,
                device_id=rec.device_id,
                device_record_id=rec.device_record_id,
                codigo=rec.codigo,
                peso=rec.peso,
                fecha=rec.fecha,
                hora=rec.hora,
                turno=rec.turno,
                status=rec.status,
                matched_animal_id=rec.matched_animal_id,
                milk_production_id=rec.milk_production_id,
                batch_id=rec.batch_id,
                created_at=rec.created_at,
                updated_at=rec.updated_at,
            )
            self.session.add(orm)
            orms.append(orm)
        await self.session.flush()
        return [self._to_domain(o) for o in orms]

    async def list_pending(
        self, tenant_id: UUID, device_id: UUID | None = None
    ) -> list[ScaleDeviceRecord]:
        conds = [
            ScaleDeviceRecordORM.tenant_id == tenant_id,
            ScaleDeviceRecordORM.status == "pending",
        ]
        if device_id is not None:
            conds.append(ScaleDeviceRecordORM.device_id == device_id)
        result = await self.session.execute(
            select(ScaleDeviceRecordORM)
            .where(and_(*conds))
            .order_by(ScaleDeviceRecordORM.created_at.desc())
        )
        return [self._to_domain(r) for r in result.scalars().all()]

    async def list_by_batch(self, tenant_id: UUID, batch_id: UUID) -> list[ScaleDeviceRecord]:
        result = await self.session.execute(
            select(ScaleDeviceRecordORM).where(
                ScaleDeviceRecordORM.tenant_id == tenant_id,
                ScaleDeviceRecordORM.batch_id == batch_id,
            )
        )
        return [self._to_domain(r) for r in result.scalars().all()]

    async def list_for_device(
        self,
        tenant_id: UUID,
        device_id: UUID,
        *,
        status: str | None = None,
        batch_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ScaleDeviceRecord]:
        conds = [
            ScaleDeviceRecordORM.tenant_id == tenant_id,
            ScaleDeviceRecordORM.device_id == device_id,
        ]
        if status is not None:
            conds.append(ScaleDeviceRecordORM.status == status)
        if batch_id is not None:
            conds.append(ScaleDeviceRecordORM.batch_id == batch_id)
        result = await self.session.execute(
            select(ScaleDeviceRecordORM)
            .where(and_(*conds))
            .order_by(ScaleDeviceRecordORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [self._to_domain(r) for r in result.scalars().all()]

    async def count_for_device(
        self,
        tenant_id: UUID,
        device_id: UUID,
        *,
        status: str | None = None,
        batch_id: UUID | None = None,
    ) -> int:
        conds = [
            ScaleDeviceRecordORM.tenant_id == tenant_id,
            ScaleDeviceRecordORM.device_id == device_id,
        ]
        if status is not None:
            conds.append(ScaleDeviceRecordORM.status == status)
        if batch_id is not None:
            conds.append(ScaleDeviceRecordORM.batch_id == batch_id)
        result = await self.session.execute(
            select(func.count()).select_from(ScaleDeviceRecordORM).where(and_(*conds))
        )
        return int(result.scalar_one() or 0)

    async def check_duplicates(self, device_id: UUID, record_ids: list[int]) -> set[int]:
        if not record_ids:
            return set()
        result = await self.session.execute(
            select(ScaleDeviceRecordORM.device_record_id).where(
                ScaleDeviceRecordORM.device_id == device_id,
                ScaleDeviceRecordORM.device_record_id.in_(record_ids),
            )
        )
        return {row[0] for row in result.all()}

    async def update_status(
        self,
        tenant_id: UUID,
        record_id: UUID,
        status: str,
        matched_animal_id: UUID | None = None,
        milk_production_id: UUID | None = None,
    ) -> ScaleDeviceRecord | None:
        data: dict = {"status": status}
        if matched_animal_id is not None:
            data["matched_animal_id"] = matched_animal_id
        if milk_production_id is not None:
            data["milk_production_id"] = milk_production_id
        stmt = (
            update(ScaleDeviceRecordORM)
            .where(
                ScaleDeviceRecordORM.tenant_id == tenant_id,
                ScaleDeviceRecordORM.id == record_id,
            )
            .values(**data)
            .returning(ScaleDeviceRecordORM)
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None
