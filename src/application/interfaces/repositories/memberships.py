from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.models.membership import Membership
from src.domain.value_objects.role import Role


class MembershipRepository(Protocol):
    async def add(self, membership: Membership) -> None: ...

    async def list_for_user(self, user_id: UUID) -> list[Membership]: ...

    async def get_role(self, user_id: UUID, tenant_id: UUID) -> Role | None: ...

    async def remove(self, user_id: UUID, tenant_id: UUID) -> None: ...

    async def update_role(self, user_id: UUID, tenant_id: UUID, new_role: Role) -> None: ...

    async def count_admins_in_tenant(self, tenant_id: UUID) -> int: ...
