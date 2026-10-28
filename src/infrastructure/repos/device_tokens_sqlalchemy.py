from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
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
        # Atomic upsert: the app may register the same token concurrently
        # (e.g. on login and on app resume), so select-then-insert races.
        dialect = self.session.get_bind().dialect.name
        insert = sqlite_insert if dialect == "sqlite" else pg_insert
        now = datetime.now(UTC)
        values = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "platform": platform,
            "app_version": app_version,
            "disabled": False,
            "last_active_at": now,
        }
        stmt = insert(DeviceTokenORM).values(id=uuid4(), token=token, **values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[DeviceTokenORM.token],
            set_={**values, "updated_at": func.now()},
        ).returning(DeviceTokenORM)
        res = await self.session.execute(stmt, execution_options={"populate_existing": True})
        return res.scalar_one()

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
            .values(disabled=True, last_active_at=datetime.now(UTC))
        )
        res = await self.session.execute(stmt)
        return res.rowcount or 0
