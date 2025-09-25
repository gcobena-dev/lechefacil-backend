from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from src.application.errors import PermissionDenied, ConflictError, NotFound
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.value_objects.role import Role


@dataclass
class RemoveMembershipInput:
    user_id: UUID
    tenant_id: UUID
    reason: str | None = None


@dataclass
class RemoveMembershipOutput:
    message: str
    user_id: UUID
    tenant_id: UUID
    removed_at: str


async def execute(
    uow: UnitOfWork,
    requester_id: UUID,
    requester_role: Role,
    payload: RemoveMembershipInput,
) -> RemoveMembershipOutput:
    if not requester_role.can_manage_users():
        raise PermissionDenied("Only admins can remove user memberships")

    async with uow:
        target_role = await uow.memberships.get_role(payload.user_id, payload.tenant_id)
        if not target_role:
            raise NotFound("User membership not found in this tenant")

        if target_role == Role.ADMIN:
            requester_role_in_tenant = await uow.memberships.get_role(requester_id, payload.tenant_id)
            if requester_role_in_tenant != Role.ADMIN:
                raise PermissionDenied("Only admins can remove other admin memberships")

            admin_count = await uow.memberships.count_admins_in_tenant(payload.tenant_id)
            if admin_count <= 1:
                raise ConflictError("Cannot remove the last admin of the tenant")

        await uow.memberships.remove(payload.user_id, payload.tenant_id)
        await uow.commit()

        return RemoveMembershipOutput(
            message="User membership removed successfully",
            user_id=payload.user_id,
            tenant_id=payload.tenant_id,
            removed_at=datetime.now(timezone.utc).isoformat(),
        )