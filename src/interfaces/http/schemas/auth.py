from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel

from src.domain.value_objects.role import Role


class MembershipSchema(BaseModel):
    tenant_id: UUID
    role: Role


class MeResponse(BaseModel):
    user_id: UUID
    active_tenant: UUID
    active_role: Role
    memberships: list[MembershipSchema]
    claims: dict[str, Any]
