from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.repositories.memberships import MembershipRepository
from src.domain.models.membership import Membership
from src.domain.value_objects.role import Role
from src.infrastructure.db.orm.membership import MembershipORM


class MembershipsSQLAlchemyRepository(MembershipRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, membership: Membership) -> None:
        orm = MembershipORM(
            user_id=membership.user_id,
            tenant_id=membership.tenant_id,
            role=membership.role,
        )
        self.session.add(orm)
        await self.session.flush()

    async def list_for_user(self, user_id: UUID) -> list[Membership]:
        stmt = select(MembershipORM).where(MembershipORM.user_id == user_id)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [
            Membership(user_id=row.user_id, tenant_id=row.tenant_id, role=row.role) for row in rows
        ]

    async def get_role(self, user_id: UUID, tenant_id: UUID) -> Role | None:
        stmt = (
            select(MembershipORM)
            .where(MembershipORM.user_id == user_id)
            .where(MembershipORM.tenant_id == tenant_id)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return row.role if row else None
