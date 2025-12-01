from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.orm.device_token import DeviceTokenORM


class DeviceTokensSQLAlchemyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        *,
        tenant_id: UUID,
        user_id: UUID,
        platform: str,
        token: str,
        app_version: str | None = None,
    ) -> DeviceTokenORM:
        # Try by unique token first
        stmt = select(DeviceTokenORM).where(DeviceTokenORM.token == token)
        res = await self.session.execute(stmt)
        existing: DeviceTokenORM | None = res.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if existing:
            await self.session.execute(
                update(DeviceTokenORM)
                .where(DeviceTokenORM.id == existing.id)
                .values(
                    tenant_id=tenant_id,
                    user_id=user_id,
                    platform=platform,
                    app_version=app_version,
                    disabled=False,
                    last_active_at=now,
                )
            )
            await self.session.flush()
            # Refresh
            await self.session.refresh(existing)
            return existing
        obj = DeviceTokenORM(
            id=uuid4(),
            tenant_id=tenant_id,
            user_id=user_id,
            platform=platform,
            token=token,
            app_version=app_version,
            disabled=False,
            last_active_at=now,
        )
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def remove_by_token(self, *, user_id: UUID, token: str) -> int:
        stmt = delete(DeviceTokenORM).where(
            DeviceTokenORM.user_id == user_id, DeviceTokenORM.token == token
        )
        res = await self.session.execute(stmt)
        return res.rowcount or 0

    async def list_for_user(self, *, user_id: UUID) -> list[DeviceTokenORM]:
        stmt = select(DeviceTokenORM).where(DeviceTokenORM.user_id == user_id)
        res = await self.session.execute(stmt)
        return list(res.scalars())

    async def disable_tokens(self, tokens: list[str]) -> int:
        """Mark tokens as disabled to avoid repeated push errors."""
        if not tokens:
            return 0
        stmt = (
            update(DeviceTokenORM)
            .where(DeviceTokenORM.token.in_(tokens))
            .values(disabled=True, last_active_at=datetime.now(timezone.utc))
        )
        res = await self.session.execute(stmt)
        return res.rowcount or 0
