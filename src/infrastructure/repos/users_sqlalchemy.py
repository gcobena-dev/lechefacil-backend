from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.errors import ConflictError, InfrastructureError, NotFound
from src.application.interfaces.repositories.users import UserRepository, UserWithRole
from src.domain.models.user import User
from src.domain.value_objects.role import Role
from src.infrastructure.db.orm.membership import MembershipORM
from src.infrastructure.db.orm.user import UserORM


class UsersSQLAlchemyRepository(UserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _to_domain(self, orm: UserORM) -> User:
        return User(
            id=orm.id,
            email=orm.email,
            hashed_password=orm.hashed_password,
            is_active=orm.is_active,
            must_change_password=orm.must_change_password,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    async def add(self, user: User) -> User:
        orm = UserORM(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            is_active=user.is_active,
            must_change_password=user.must_change_password,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
        self.session.add(orm)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            raise ConflictError("Email already registered") from exc
        return self._to_domain(orm)

    async def get(self, user_id: UUID) -> User | None:
        stmt = select(UserORM).where(UserORM.id == user_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserORM).where(UserORM.email == email.lower())
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def update_password(self, user_id: UUID, hashed_password: str) -> None:
        stmt = (
            update(UserORM)
            .where(UserORM.id == user_id)
            .values(hashed_password=hashed_password, must_change_password=False)
        )
        result = await self.session.execute(stmt)
        if result.rowcount == 0:
            raise NotFound("User not found")

    async def set_active(self, user_id: UUID, is_active: bool) -> None:
        stmt = update(UserORM).where(UserORM.id == user_id).values(is_active=is_active)
        result = await self.session.execute(stmt)
        if result.rowcount == 0:
            raise InfrastructureError("Failed to update user status")

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        page: int = 1,
        limit: int = 10,
        role_filter: Role | None = None,
        search: str | None = None,
    ) -> tuple[list[UserWithRole], int]:
        base_query = (
            select(UserORM, MembershipORM.role)
            .join(MembershipORM, UserORM.id == MembershipORM.user_id)
            .where(MembershipORM.tenant_id == tenant_id)
        )

        if role_filter:
            base_query = base_query.where(MembershipORM.role == role_filter)

        if search:
            search_pattern = f"%{search.lower()}%"
            base_query = base_query.where(
                or_(
                    func.lower(UserORM.email).like(search_pattern),
                )
            )

        count_query = select(func.count()).select_from(base_query.subquery())
        total = await self.session.scalar(count_query) or 0

        offset = (page - 1) * limit
        stmt = base_query.offset(offset).limit(limit).order_by(UserORM.created_at.desc())

        result = await self.session.execute(stmt)
        rows = result.fetchall()

        users_with_roles = []
        for user_orm, role in rows:
            user = self._to_domain(user_orm)
            users_with_roles.append(UserWithRole(user=user, role=role))

        return users_with_roles, total
