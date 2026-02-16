from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from src.application.errors import ConflictError, NotFound, PermissionDenied
from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.value_objects.role import Role


@dataclass
class UpdateMembershipRoleInput:
    user_id: UUID
    tenant_id: UUID
    new_role: Role


@dataclass
class UpdateMembershipRoleOutput:
    message: str
    user_id: UUID
    tenant_id: UUID
    new_role: Role
    updated_at: str


async def execute(
    uow: UnitOfWork,
    requester_id: UUID,
    requester_role: Role,
    payload: UpdateMembershipRoleInput,
) -> UpdateMembershipRoleOutput:
    if not requester_role.can_manage_users():
        raise PermissionDenied("Only admins can change user roles")

    if payload.user_id == requester_id:
        raise PermissionDenied("Cannot change your own role")

    async with uow:
        target_role = await uow.memberships.get_role(payload.user_id, payload.tenant_id)
        if not target_role:
            raise NotFound("User membership not found in this tenant")

        if target_role == payload.new_role:
            raise ConflictError("User already has this role")

        if target_role == Role.ADMIN:
            admin_count = await uow.memberships.count_admins_in_tenant(payload.tenant_id)
            if admin_count <= 1:
                raise ConflictError("Cannot change the role of the last admin of the tenant")

        await uow.memberships.update_role(payload.user_id, payload.tenant_id, payload.new_role)
        await uow.commit()

        return UpdateMembershipRoleOutput(
            message="User role updated successfully",
            user_id=payload.user_id,
            tenant_id=payload.tenant_id,
            new_role=payload.new_role,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
