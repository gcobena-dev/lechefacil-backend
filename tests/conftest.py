from __future__ import annotations

import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import cast
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///default.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_ACCESS_TOKEN_EXPIRES_MINUTES", "60")
os.environ.setdefault("JWT_ISSUER", "https://issuer.test")
os.environ.setdefault("JWT_AUDIENCE", "test-audience")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

# ruff: noqa: E402
from src.config.settings import Settings
from src.domain.value_objects.role import Role
from src.infrastructure.auth.password import PasswordHasher
from src.infrastructure.db.base import Base

# SQLite does not support named schemas; clear default schema before ORM imports.
Base.metadata.schema = None

from src.infrastructure.db.orm import animal, attachment, membership, user  # noqa: F401
from src.infrastructure.db.orm.membership import MembershipORM
from src.infrastructure.db.orm.user import UserORM
from src.interfaces.http.main import create_app


@pytest.fixture(scope="session")
def tenant_id() -> UUID:
    return uuid4()


@pytest.fixture()
def password_hasher() -> PasswordHasher:
    return PasswordHasher()


@pytest.fixture()
def test_settings(tmp_path) -> Settings:
    db_path = tmp_path / "test.db"
    return Settings.model_validate(
        {
            "database_url": f"sqlite+aiosqlite:///{db_path}",
            "tenant_header": "X-Tenant-ID",
            "log_level": "INFO",
            "environment": "test",
            "jwt_secret_key": "test-secret",
            "jwt_algorithm": "HS256",
            "jwt_access_token_expires_minutes": 60,
            "jwt_issuer": "https://issuer.test",
            "jwt_audience": "test-audience",
        }
    )


@pytest.fixture()
def app(test_settings: Settings, password_hasher: PasswordHasher):
    return create_app(settings=test_settings, password_hasher=password_hasher)


@pytest.fixture()
def token_factory(app):
    jwt_service = app.state.jwt_service

    def _create(user_id: UUID, **extra_claims):
        return jwt_service.create_access_token(subject=user_id, extra_claims=extra_claims or None)

    return _create


@pytest.fixture()
async def client(app) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        engine = app.state.engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        yield client


@pytest.fixture()
async def seeded_memberships(
    app, client, tenant_id: UUID, password_hasher: PasswordHasher
) -> dict[str, UUID]:
    admin_id = uuid4()
    manager_id = uuid4()
    worker_id = uuid4()
    vet_id = uuid4()
    # type: ignore[attr-defined]
    async with app.state.session_factory() as session:
        async_session = cast(AsyncSession, session)
        async_session.add_all(
            [
                UserORM(
                    id=admin_id,
                    email="admin@example.com",
                    hashed_password=password_hasher.hash("secret"),
                    is_active=True,
                ),
                UserORM(
                    id=manager_id,
                    email="manager@example.com",
                    hashed_password=password_hasher.hash("secret"),
                    is_active=True,
                ),
                UserORM(
                    id=worker_id,
                    email="worker@example.com",
                    hashed_password=password_hasher.hash("secret"),
                    is_active=True,
                ),
                UserORM(
                    id=vet_id,
                    email="vet@example.com",
                    hashed_password=password_hasher.hash("secret"),
                    is_active=True,
                ),
            ]
        )
        async_session.add_all(
            [
                MembershipORM(user_id=admin_id, tenant_id=tenant_id, role=Role.ADMIN),
                MembershipORM(user_id=manager_id, tenant_id=tenant_id, role=Role.MANAGER),
                MembershipORM(user_id=worker_id, tenant_id=tenant_id, role=Role.WORKER),
                MembershipORM(user_id=vet_id, tenant_id=tenant_id, role=Role.VETERINARIAN),
            ]
        )
        await async_session.commit()
    return {"admin": admin_id, "manager": manager_id, "worker": worker_id, "vet": vet_id}
