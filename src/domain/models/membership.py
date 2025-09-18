from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.domain.value_objects.role import Role


@dataclass(slots=True, frozen=True)
class Membership:
    user_id: UUID
    tenant_id: UUID
    role: Role
