from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.scale_device import ScaleDevice
from src.infrastructure.db.orm.scale_device import ScaleDeviceORM


class ScaleDevicesSQLAlchemyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: ScaleDeviceORM) -> ScaleDevice:
        return ScaleDevice(
            id=orm.id,
            tenant_id=orm.tenant_id,
            name=orm.name,
            api_key=orm.api_key,
            wifi_ssid=orm.wifi_ssid,
            wifi_password=orm.wifi_password,
            is_active=orm.is_active,
            last_seen_at=orm.last_seen_at,
            firmware_version=orm.firmware_version,
            pairing_pin=orm.pairing_pin,
            pairing_pin_expires_at=orm.pairing_pin_expires_at,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    async def get_by_api_key(self, api_key: str) -> ScaleDevice | None:
        result = await self.session.execute(
            select(ScaleDeviceORM).where(ScaleDeviceORM.api_key == api_key)
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get(self, tenant_id: UUID, device_id: UUID) -> ScaleDevice | None:
        result = await self.session.execute(
            select(ScaleDeviceORM).where(
                ScaleDeviceORM.tenant_id == tenant_id,
                ScaleDeviceORM.id == device_id,
            )
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_for_tenant(self, tenant_id: UUID) -> list[ScaleDevice]:
        result = await self.session.execute(
            select(ScaleDeviceORM)
            .where(ScaleDeviceORM.tenant_id == tenant_id)
            .order_by(ScaleDeviceORM.created_at.desc())
        )
        return [self._to_domain(r) for r in result.scalars().all()]

    async def add(self, device: ScaleDevice) -> ScaleDevice:
        orm = ScaleDeviceORM(
            id=device.id,
            tenant_id=device.tenant_id,
            name=device.name,
            api_key=device.api_key,
            wifi_ssid=device.wifi_ssid,
            wifi_password=device.wifi_password,
            is_active=device.is_active,
            last_seen_at=device.last_seen_at,
            firmware_version=device.firmware_version,
            pairing_pin=device.pairing_pin,
            pairing_pin_expires_at=device.pairing_pin_expires_at,
            created_at=device.created_at,
            updated_at=device.updated_at,
        )
        self.session.add(orm)
        await self.session.flush()
        return self._to_domain(orm)

    async def update(self, tenant_id: UUID, device_id: UUID, data: dict) -> ScaleDevice | None:
        stmt = (
            update(ScaleDeviceORM)
            .where(ScaleDeviceORM.tenant_id == tenant_id, ScaleDeviceORM.id == device_id)
            .values(**data)
            .returning(ScaleDeviceORM)
        )
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_pairing_pin(self, pin: str) -> ScaleDevice | None:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(ScaleDeviceORM).where(
                ScaleDeviceORM.pairing_pin == pin,
                ScaleDeviceORM.is_active.is_(True),
                ScaleDeviceORM.pairing_pin_expires_at > now,
            )
        )
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def clear_pairing_pin(self, device_id: UUID) -> None:
        stmt = (
            update(ScaleDeviceORM)
            .where(ScaleDeviceORM.id == device_id)
            .values(pairing_pin=None, pairing_pin_expires_at=None)
        )
        await self.session.execute(stmt)

    async def update_last_seen(self, device_id: UUID, firmware_version: str | None = None) -> None:
        data: dict = {"last_seen_at": datetime.now(timezone.utc)}
        if firmware_version is not None:
            data["firmware_version"] = firmware_version
        stmt = update(ScaleDeviceORM).where(ScaleDeviceORM.id == device_id).values(**data)
        await self.session.execute(stmt)
