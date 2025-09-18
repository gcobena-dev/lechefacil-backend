from __future__ import annotations

import os
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///default.db")
os.environ.setdefault("OIDC_ISSUER", "https://issuer.test")
os.environ.setdefault("JWKS_URL", "https://issuer.test/.well-known/jwks.json")
os.environ.setdefault("OIDC_AUDIENCE", "test-audience")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

# ruff: noqa: E402
from src.application.errors import AuthError
from src.config.settings import Settings
from src.domain.value_objects.role import Role
from src.infrastructure.db.base import Base
from src.infrastructure.db.orm import animal, membership  # noqa: F401
from src.infrastructure.db.orm.membership import MembershipORM
from src.interfaces.http.main import create_app


class StubJWKSClient:
    def __init__(self, *, issuer: str, audience: str) -> None:
        self.issuer = issuer
        self.audience = audience

    async def decode_token(self, token: str, *, issuer: str, audience: str) -> dict[str, Any]:
        if issuer != self.issuer or audience != self.audience:
            raise AuthError("Invalid token issuer or audience")
        return {"sub": token, "iss": issuer, "aud": audience}


@pytest.fixture(scope="session")
def tenant_id() -> UUID:
    return uuid4()


@pytest.fixture()
def test_settings(tmp_path) -> Settings:
    db_path = tmp_path / "test.db"
    return Settings.model_validate(
        {
            "database_url": f"sqlite+aiosqlite:///{db_path}",
            "oidc_issuer": "https://issuer.test",
            "jwks_url": "https://issuer.test/.well-known/jwks.json",
            "oidc_audience": "test-audience",
            "tenant_header": "X-Tenant-ID",
            "log_level": "INFO",
            "environment": "test",
            "jwks_cache_ttl": 0,
        }
    )


@pytest.fixture()
def jwks_client(test_settings: Settings) -> StubJWKSClient:
    return StubJWKSClient(
        issuer=str(test_settings.oidc_issuer),
        audience=test_settings.oidc_audience,
    )


@pytest.fixture()
def app(test_settings: Settings, jwks_client: StubJWKSClient):
    return create_app(settings=test_settings, jwks_client=jwks_client)


@pytest.fixture()
async def client(app) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        engine = app.state.engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        yield client


@pytest.fixture()
async def seeded_memberships(app, client, tenant_id: UUID) -> dict[str, UUID]:
    admin_id = uuid4()
    manager_id = uuid4()
    worker_id = uuid4()
    async with app.state.session_factory() as session:  # type: ignore[attr-defined]
        async_session = cast(AsyncSession, session)
        async_session.add_all(
            [
                MembershipORM(user_id=admin_id, tenant_id=tenant_id, role=Role.ADMIN),
                MembershipORM(user_id=manager_id, tenant_id=tenant_id, role=Role.MANAGER),
                MembershipORM(user_id=worker_id, tenant_id=tenant_id, role=Role.WORKER),
            ]
        )
        await async_session.commit()
    return {"admin": admin_id, "manager": manager_id, "worker": worker_id}
