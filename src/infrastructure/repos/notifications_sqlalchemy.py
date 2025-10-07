from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.models.notification import Notification
from src.infrastructure.db.orm.notification import NotificationORM


class NotificationsSQLAlchemyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: NotificationORM) -> Notification:
        data = json.loads(orm.data) if orm.data else None
        return Notification(
            id=orm.id,
            tenant_id=orm.tenant_id,
            user_id=orm.user_id,
            type=orm.type,
            title=orm.title,
            message=orm.message,
            data=data,
            read=orm.read,
            created_at=orm.created_at,
            read_at=orm.read_at,
        )

    def _to_orm(self, notification: Notification) -> NotificationORM:
        data_str = json.dumps(notification.data) if notification.data else None
        return NotificationORM(
            id=notification.id,
            tenant_id=notification.tenant_id,
            user_id=notification.user_id,
            type=notification.type,
            title=notification.title,
            message=notification.message,
            data=data_str,
            read=notification.read,
            created_at=notification.created_at,
            read_at=notification.read_at,
        )

    async def add(self, notification: Notification) -> Notification:
        orm = self._to_orm(notification)
        self.session.add(orm)
        await self.session.flush()
        return self._to_domain(orm)

    async def get(self, notification_id: UUID) -> Notification | None:
        stmt = select(NotificationORM).where(NotificationORM.id == notification_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def list_by_user(
        self,
        tenant_id: UUID,
        user_id: UUID,
        *,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        stmt = (
            select(NotificationORM)
            .where(NotificationORM.tenant_id == tenant_id, NotificationORM.user_id == user_id)
            .order_by(NotificationORM.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if unread_only:
            stmt = stmt.where(NotificationORM.read == False)  # noqa: E712

        result = await self.session.execute(stmt)
        return [self._to_domain(orm) for orm in result.scalars().all()]

    async def count_unread(self, tenant_id: UUID, user_id: UUID) -> int:
        stmt = select(func.count()).where(
            NotificationORM.tenant_id == tenant_id,
            NotificationORM.user_id == user_id,
            NotificationORM.read == False,  # noqa: E712
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def mark_as_read(self, notification_ids: list[UUID]) -> int:
        stmt = (
            update(NotificationORM)
            .where(NotificationORM.id.in_(notification_ids), NotificationORM.read == False)  # noqa: E712
            .values(read=True, read_at=func.now())
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0

    async def mark_all_as_read(self, tenant_id: UUID, user_id: UUID) -> int:
        stmt = (
            update(NotificationORM)
            .where(
                NotificationORM.tenant_id == tenant_id,
                NotificationORM.user_id == user_id,
                NotificationORM.read == False,  # noqa: E712
            )
            .values(read=True, read_at=func.now())
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0
