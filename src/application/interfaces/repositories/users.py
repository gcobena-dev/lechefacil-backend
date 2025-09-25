from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.models.user import User
from src.domain.value_objects.role import Role


class UserWithRole:
    def __init__(self, user: User, role: Role, last_login: str | None = None):
        self.user = user
        self.role = role
        self.last_login = last_login

    @property
    def id(self) -> UUID:
        return self.user.id

    @property
    def email(self) -> str:
        return self.user.email

    @property
    def is_active(self) -> bool:
        return self.user.is_active

    @property
    def created_at(self) -> str:
        return self.user.created_at.isoformat()


class UserRepository(Protocol):
    async def add(self, user: User) -> User: ...

    async def get(self, user_id: UUID) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def update_password(self, user_id: UUID, hashed_password: str) -> None: ...

    async def set_active(self, user_id: UUID, is_active: bool) -> None: ...

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        page: int = 1,
        limit: int = 10,
        role_filter: Role | None = None,
        search: str | None = None,
    ) -> tuple[list[UserWithRole], int]: ...
