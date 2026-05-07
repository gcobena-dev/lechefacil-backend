from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from src.config.settings import Settings
from src.infrastructure.auth.password import PasswordHasher
from src.infrastructure.db.base import Base
from src.interfaces.http.deps import get_app_settings
from src.interfaces.http.main import create_app


BOOTSTRAP_KEY = "test-bootstrap-key-please-rotate"


@pytest.fixture()
def settings_with_bootstrap(tmp_path) -> Settings:
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
            "bootstrap_secret_key": BOOTSTRAP_KEY,
        }
    )


@pytest.fixture()
def app_with_bootstrap(settings_with_bootstrap: Settings):
    app = create_app(settings=settings_with_bootstrap, password_hasher=PasswordHasher())
    app.dependency_overrides[get_app_settings] = lambda: settings_with_bootstrap
    return app


@pytest.fixture()
async def boot_client(app_with_bootstrap) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app_with_bootstrap)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        engine = app_with_bootstrap.state.engine
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        yield client


@pytest.mark.asyncio
async def test_register_tenant_for_new_email(boot_client: AsyncClient):
    resp = await boot_client.post(
        "/api/v1/auth/register-tenant",
        headers={"X-Bootstrap-Key": BOOTSTRAP_KEY},
        json={"email": "brand.new@example.com"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "brand.new@example.com"
    assert "tenant_id" in body
    assert "user_id" in body


@pytest.mark.asyncio
async def test_register_tenant_for_self_registered_user(boot_client: AsyncClient):
    # Step 1: user self-registers (simulates current prod state of javierclub2020)
    signin = await boot_client.post(
        "/api/v1/auth/signin",
        json={"email": "javier@example.com", "password": "MyP4ss!word"},
    )
    assert signin.status_code == 201, signin.text
    self_user_id = signin.json()["user_id"]

    # Step 2: admin "approves" by hitting register-tenant with bootstrap key
    approve = await boot_client.post(
        "/api/v1/auth/register-tenant",
        headers={"X-Bootstrap-Key": BOOTSTRAP_KEY},
        json={"email": "javier@example.com"},
    )
    assert approve.status_code == 201, approve.text
    body = approve.json()

    # Should reuse the same user, not create a new one
    assert body["user_id"] == self_user_id
    assert body["email"] == "javier@example.com"
    assert "tenant_id" in body


@pytest.mark.asyncio
async def test_register_tenant_rejects_invalid_bootstrap_key(boot_client: AsyncClient):
    resp = await boot_client.post(
        "/api/v1/auth/register-tenant",
        headers={"X-Bootstrap-Key": "wrong-key"},
        json={"email": "anyone@example.com"},
    )
    assert resp.status_code == 403, resp.text
