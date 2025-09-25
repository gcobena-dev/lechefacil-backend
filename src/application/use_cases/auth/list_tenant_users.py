from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.value_objects.role import Role


@dataclass
class ListTenantUsersInput:
    tenant_id: UUID
    page: int = 1
    limit: int = 10
    role_filter: Role | None = None
    search: str | None = None


@dataclass
class UserResult:
    id: UUID
    email: str
    role: Role
    is_active: bool
    created_at: str
    last_login: str | None = None


@dataclass
class ListTenantUsersOutput:
    users: list[UserResult]
    total: int
    page: int
    limit: int


async def execute(uow: UnitOfWork, payload: ListTenantUsersInput) -> ListTenantUsersOutput:
    async with uow:
        users_with_roles, total = await uow.users.list_by_tenant(
            tenant_id=payload.tenant_id,
            page=payload.page,
            limit=payload.limit,
            role_filter=payload.role_filter,
            search=payload.search,
        )

        user_results = []
        for user_with_role in users_with_roles:
            user_results.append(
                UserResult(
                    id=user_with_role.id,
                    email=user_with_role.email,
                    role=user_with_role.role,
                    is_active=user_with_role.is_active,
                    created_at=user_with_role.created_at,
                    last_login=user_with_role.last_login,
                )
            )

        return ListTenantUsersOutput(
            users=user_results,
            total=total,
            page=payload.page,
            limit=payload.limit,
        )