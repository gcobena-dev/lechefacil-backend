from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.domain.models.membership import Membership
from src.domain.value_objects.role import Role


@dataclass(slots=True)
class MembershipInfo:
    tenant_id: UUID
    role: Role


@dataclass(slots=True)
class MeResult:
    user_id: UUID
    email: str
    active_tenant: UUID
    active_role: Role
    memberships: list[MembershipInfo]
    claims: dict[str, Any]


async def execute(
    *,
    user_id: UUID,
    email: str,
    active_tenant: UUID,
    active_role: Role,
    memberships: list[Membership],
    claims: dict[str, Any],
) -> MeResult:
    membership_infos = [MembershipInfo(tenant_id=m.tenant_id, role=m.role) for m in memberships]
    return MeResult(
        user_id=user_id,
        email=email,
        active_tenant=active_tenant,
        active_role=active_role,
        memberships=membership_infos,
        claims=claims,
    )
