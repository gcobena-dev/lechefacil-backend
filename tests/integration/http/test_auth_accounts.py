from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_login_with_internal_token(client, seeded_memberships, tenant_id):
    payload = {
        "email": "admin@example.com",
        "password": "secret",
        "tenant_id": str(tenant_id),
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    token = data["access_token"]

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
    }
    me = await client.get("/api/v1/me", headers=headers)
    assert me.status_code == 200
    details = me.json()
    assert details["email"] == "admin@example.com"
    assert details["active_role"] == "ADMIN"


@pytest.mark.asyncio
async def test_register_and_login_new_user(client, seeded_memberships, tenant_id):
    admin_id = seeded_memberships["admin"]
    headers = {
        "Authorization": f"Bearer {admin_id}",
        "X-Tenant-ID": str(tenant_id),
    }
    register_payload = {
        "email": "new.worker@example.com",
        "password": "workerpass",
        "tenant_id": str(tenant_id),
        "role": "WORKER",
        "is_active": True,
    }
    register_response = await client.post(
        "/api/v1/auth/register", json=register_payload, headers=headers
    )
    assert register_response.status_code == 201

    login_payload = {
        "email": "new.worker@example.com",
        "password": "workerpass",
        "tenant_id": str(tenant_id),
    }
    login_response = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_response.status_code == 200
    data = login_response.json()
    token = data["access_token"]

    me_headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
    }
    me = await client.get("/api/v1/me", headers=me_headers)
    assert me.status_code == 200
    me_data = me.json()
    assert me_data["email"] == "new.worker@example.com"
    assert me_data["active_role"] == "WORKER"


@pytest.mark.asyncio
async def test_change_password_self(client, seeded_memberships, tenant_id):
    login_payload = {
        "email": "manager@example.com",
        "password": "secret",
        "tenant_id": str(tenant_id),
    }
    login_response = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(tenant_id),
    }
    change_payload = {
        "current_password": "secret",
        "new_password": "newsecret",
    }
    change_response = await client.post(
        "/api/v1/auth/change-password", json=change_payload, headers=headers
    )
    assert change_response.status_code == 200

    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "manager@example.com", "password": "secret", "tenant_id": str(tenant_id)},
    )
    assert bad_login.status_code == 401

    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "manager@example.com", "password": "newsecret", "tenant_id": str(tenant_id)},
    )
    assert new_login.status_code == 200
