from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.application.interfaces.unit_of_work import UnitOfWork


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, echo=False, future=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


class SQLAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory
        self.session: AsyncSession | None = None
        self.animals = None
        self.users = None
        self.memberships = None

    async def __aenter__(self) -> UnitOfWork:
        self.session = self._session_factory()
        from src.infrastructure.repos.animals_sqlalchemy import AnimalsSQLAlchemyRepository
        from src.infrastructure.repos.memberships_sqlalchemy import MembershipsSQLAlchemyRepository
        from src.infrastructure.repos.users_sqlalchemy import UsersSQLAlchemyRepository

        self.animals = AnimalsSQLAlchemyRepository(self.session)
        self.users = UsersSQLAlchemyRepository(self.session)
        self.memberships = MembershipsSQLAlchemyRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if not self.session:
            return
        try:
            if exc:
                await self.session.rollback()
        finally:
            await self.session.close()
            self.session = None
            self.animals = None
            self.users = None
            self.memberships = None

    async def commit(self) -> None:
        if not self.session:
            return
        await self.session.commit()

    async def rollback(self) -> None:
        if not self.session:
            return
        await self.session.rollback()
