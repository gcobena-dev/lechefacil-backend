from __future__ import annotations

from uuid import UUID


async def test_get_tenant_identity_returns_default_name(
    app, client, seeded_memberships, tenant_id: UUID, token_factory
):
    token = token_factory(seeded_memberships["admin"])
    headers = {
        "Authorization": f"Bearer {token}",
        app.state.settings.tenant_header: str(tenant_id),
    }

    resp = await client.get("/api/v1/settings/tenant", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tenant_id"] == str(tenant_id)
    assert body["name"] == "Mi Finca"
    assert body["location"] is None


async def test_patch_tenant_identity_updates_name_and_location(
    app, client, seeded_memberships, tenant_id: UUID, token_factory
):
    token = token_factory(seeded_memberships["admin"])
    headers = {
        "Authorization": f"Bearer {token}",
        app.state.settings.tenant_header: str(tenant_id),
    }

    resp = await client.patch(
        "/api/v1/settings/tenant",
        headers=headers,
        json={"name": "Finca Las Palmas", "location": "Ecuador"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "Finca Las Palmas"
    assert body["location"] == "Ecuador"

    follow_up = await client.get("/api/v1/settings/tenant", headers=headers)
    assert follow_up.json()["name"] == "Finca Las Palmas"


async def test_patch_tenant_identity_requires_admin_role(
    app, client, seeded_memberships, tenant_id: UUID, token_factory
):
    token = token_factory(seeded_memberships["worker"])
    headers = {
        "Authorization": f"Bearer {token}",
        app.state.settings.tenant_header: str(tenant_id),
    }

    resp = await client.patch(
        "/api/v1/settings/tenant",
        headers=headers,
        json={"name": "Finca Tomada"},
    )
    assert resp.status_code == 403, resp.text


async def test_patch_tenant_identity_rejects_empty_name(
    app, client, seeded_memberships, tenant_id: UUID, token_factory
):
    token = token_factory(seeded_memberships["admin"])
    headers = {
        "Authorization": f"Bearer {token}",
        app.state.settings.tenant_header: str(tenant_id),
    }

    resp = await client.patch(
        "/api/v1/settings/tenant",
        headers=headers,
        json={"name": "   "},
    )
    assert resp.status_code == 422, resp.text


async def test_my_tenants_includes_tenant_name(
    app, client, seeded_memberships, tenant_id: UUID, token_factory
):
    # Pre-condition: rename the tenant to verify hydration through /auth/my-tenants
    admin_token = token_factory(seeded_memberships["admin"])
    headers = {
        "Authorization": f"Bearer {admin_token}",
        app.state.settings.tenant_header: str(tenant_id),
    }
    rename = await client.patch(
        "/api/v1/settings/tenant", headers=headers, json={"name": "Finca Test"}
    )
    assert rename.status_code == 200

    resp = await client.get(
        "/api/v1/auth/my-tenants",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list)
    assert any(m["tenant_id"] == str(tenant_id) and m["tenant_name"] == "Finca Test" for m in body)
