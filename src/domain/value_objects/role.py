from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    WORKER = "WORKER"

    def can_create(self) -> bool:
        return self in {Role.ADMIN, Role.MANAGER}

    def can_update(self) -> bool:
        return self in {Role.ADMIN, Role.MANAGER}

    def can_delete(self) -> bool:
        return self is Role.ADMIN
