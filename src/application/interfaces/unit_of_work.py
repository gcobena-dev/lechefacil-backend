from __future__ import annotations

from typing import Protocol

from src.application.interfaces.repositories.animals import AnimalRepository
from src.application.interfaces.repositories.memberships import MembershipRepository
from src.application.interfaces.repositories.users import UserRepository


class UnitOfWork(Protocol):
    animals: AnimalRepository
    users: UserRepository
    memberships: MembershipRepository

    async def __aenter__(self) -> UnitOfWork: ...

    async def __aexit__(self, exc_type, exc, tb) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
