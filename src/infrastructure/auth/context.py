from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.errors import PermissionDenied
from src.domain.models.membership import Membership
from src.domain.value_objects.role import Role
from src.infrastructure.db.orm.membership import MembershipORM


@dataclass(slots=True)
class AuthContext:
    user_id: UUID
    tenant_id: UUID
    role: Role
    memberships: list[Membership]
    claims: dict[str, Any]

    def require_roles(self, allowed: Iterable[Role]) -> None:
        if self.role not in set(allowed):
            raise PermissionDenied("Role not allowed for this action")


async def fetch_memberships(session: AsyncSession, user_id: UUID) -> list[Membership]:
    stmt = select(MembershipORM).where(MembershipORM.user_id == user_id)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [Membership(user_id=row.user_id, tenant_id=row.tenant_id, role=row.role) for row in rows]


def select_active_role(memberships: list[Membership], tenant_id: UUID) -> Role:
    for membership in memberships:
        if membership.tenant_id == tenant_id:
            return membership.role
    raise PermissionDenied("User does not belong to tenant")
