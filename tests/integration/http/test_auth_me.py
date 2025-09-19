from __future__ import annotations


async def test_me_returns_user_context(client, seeded_memberships, tenant_id):
    admin_id = seeded_memberships["admin"]
    headers = {
        "Authorization": f"Bearer {admin_id}",
        "X-Tenant-ID": str(tenant_id),
    }
    response = await client.get("/api/v1/me", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == str(admin_id)
    assert payload["email"] == "admin@example.com"
    assert payload["active_tenant"] == str(tenant_id)
    assert payload["active_role"] == "ADMIN"
    assert any(m["tenant_id"] == str(tenant_id) for m in payload["memberships"])
