from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from src.application.errors import ConflictError
from src.application.use_cases.auth import bootstrap_tenant
from src.domain.models.membership import Membership
from src.domain.models.tenant_config import TenantConfig
from src.domain.models.user import User
from src.domain.value_objects.role import Role


class StubUsersRepo:
    def __init__(self, existing: User | None = None) -> None:
        self.existing = existing
        self.added: User | None = None

    async def get_by_email(self, email: str) -> User | None:
        if self.existing and self.existing.email == email.lower():
            return self.existing
        return None

    async def add(self, user: User) -> User:
        self.added = user
        return user


class StubMembershipsRepo:
    def __init__(self, existing_role: Role | None = None) -> None:
        self.existing_role = existing_role
        self.added: Membership | None = None

    async def get_role(self, user_id: UUID, tenant_id: UUID) -> Role | None:
        return self.existing_role

    async def add(self, membership: Membership) -> None:
        self.added = membership


class StubTenantConfigRepo:
    def __init__(self) -> None:
        self.upserted: TenantConfig | None = None

    async def get(self, tenant_id: UUID) -> TenantConfig | None:
        return None

    async def upsert(self, cfg: TenantConfig) -> None:
        self.upserted = cfg


class StubHasher:
    def hash(self, password: str) -> str:
        return f"hashed::{password}"


def make_uow(users: StubUsersRepo, memberships: StubMembershipsRepo) -> SimpleNamespace:
    commits: list[bool] = []

    async def commit():
        commits.append(True)

    async def rollback():
        return None

    return SimpleNamespace(
        users=users,
        memberships=memberships,
        tenant_config=StubTenantConfigRepo(),
        commit=commit,
        rollback=rollback,
        commits=commits,
    )


@pytest.mark.asyncio
async def test_bootstrap_creates_user_tenant_membership_for_new_email():
    users = StubUsersRepo(existing=None)
    memberships = StubMembershipsRepo()
    uow = make_uow(users, memberships)

    result = await bootstrap_tenant.execute(
        uow=uow,
        payload=bootstrap_tenant.RegisterTenantInput(
            email="new@example.com", password="pwd123"
        ),
        password_hasher=StubHasher(),
    )

    assert result.created_user is True
    assert result.email == "new@example.com"
    assert users.added is not None
    assert users.added.hashed_password == "hashed::pwd123"
    assert memberships.added is not None
    assert memberships.added.role is Role.ADMIN
    assert memberships.added.user_id == users.added.id
    assert memberships.added.tenant_id == result.tenant_id
    assert uow.tenant_config.upserted is not None
    assert uow.commits == [True]


@pytest.mark.asyncio
async def test_bootstrap_assigns_new_tenant_to_existing_user():
    existing = User.create(email="javier@example.com", hashed_password="prev-hash")
    users = StubUsersRepo(existing=existing)
    memberships = StubMembershipsRepo(existing_role=None)
    uow = make_uow(users, memberships)

    result = await bootstrap_tenant.execute(
        uow=uow,
        payload=bootstrap_tenant.RegisterTenantInput(
            email="javier@example.com", password="ignored"
        ),
        password_hasher=StubHasher(),
    )

    assert result.created_user is False
    assert result.user_id == existing.id
    assert result.email == existing.email
    assert users.added is None  # never re-creates the user
    assert memberships.added is not None
    assert memberships.added.user_id == existing.id
    assert memberships.added.tenant_id == result.tenant_id
    assert memberships.added.role is Role.ADMIN
    assert uow.tenant_config.upserted is not None
    assert uow.commits == [True]


@pytest.mark.asyncio
async def test_bootstrap_rejects_existing_membership_in_same_tenant():
    existing = User.create(email="javier@example.com", hashed_password="prev-hash")
    users = StubUsersRepo(existing=existing)
    memberships = StubMembershipsRepo(existing_role=Role.WORKER)
    uow = make_uow(users, memberships)

    fixed_tenant = uuid4()
    with pytest.raises(ConflictError):
        await bootstrap_tenant.execute(
            uow=uow,
            payload=bootstrap_tenant.RegisterTenantInput(
                email="javier@example.com",
                password="ignored",
                tenant_id=fixed_tenant,
            ),
            password_hasher=StubHasher(),
        )

    assert memberships.added is None
    assert uow.commits == []
