from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.models.user import User


class UserRepository(Protocol):
    async def add(self, user: User) -> User: ...

    async def get(self, user_id: UUID) -> User | None: ...

    async def get_by_email(self, email: str) -> User | None: ...

    async def update_password(self, user_id: UUID, hashed_password: str) -> None: ...

    async def set_active(self, user_id: UUID, is_active: bool) -> None: ...
