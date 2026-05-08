from __future__ import annotations

from uuid import UUID


async def test_submit_creates_pending_request(app, client):
    resp = await client.post(
        "/api/v1/access-requests/",
        json={
            "full_name": "Juan Test",
            "email": "juan.test@example.com",
            "phone_number": "0999999999",
            "farm_name": "Mi Finca Test",
            "farm_location": "Manabí",
            "requested_role": "admin",
            "message": "Me gustaría acceso",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert UUID(body["id"])


async def test_submit_dedupe_open_request(app, client):
    payload = {
        "full_name": "Dup Test",
        "email": "dup.test@example.com",
        "farm_name": "Finca",
        "farm_location": "X",
        "requested_role": "admin",
    }
    first = await client.post("/api/v1/access-requests/", json=payload)
    assert first.status_code == 200, first.text
    second = await client.post("/api/v1/access-requests/", json=payload)
    assert second.status_code == 409, second.text


async def test_list_requires_super_admin(app, client, seeded_memberships, token_factory):
    admin_token = token_factory(seeded_memberships["admin"])
    resp = await client.get(
        "/api/v1/access-requests/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 403, resp.text


async def test_super_admin_can_list_and_approve(app, client, super_admin_user: UUID, token_factory):
    submit = await client.post(
        "/api/v1/access-requests/",
        json={
            "full_name": "Aprobada",
            "email": "approved.user@example.com",
            "farm_name": "Finca Aprobada",
            "farm_location": "Loja",
            "requested_role": "admin",
        },
    )
    assert submit.status_code == 200, submit.text
    request_id = submit.json()["id"]

    sa_token = token_factory(super_admin_user)
    headers = {"Authorization": f"Bearer {sa_token}"}

    listing = await client.get("/api/v1/access-requests/?status=pending", headers=headers)
    assert listing.status_code == 200, listing.text
    items = listing.json()["items"]
    assert any(item["id"] == request_id for item in items)

    approve_resp = await client.post(
        f"/api/v1/access-requests/{request_id}/approve",
        headers=headers,
        json={"notes": "OK!"},
    )
    assert approve_resp.status_code == 200, approve_resp.text
    body = approve_resp.json()
    assert body["status"] == "approved"
    assert body["created_tenant_id"] is not None
    assert body["decision_notes"] == "OK!"

    # Idempotent: second call returns same state
    second = await client.post(f"/api/v1/access-requests/{request_id}/approve", headers=headers)
    assert second.status_code == 200
    assert second.json()["status"] == "approved"


async def test_super_admin_reject_then_resubmit_allowed(
    app, client, super_admin_user: UUID, token_factory
):
    payload = {
        "full_name": "Rechazo Test",
        "email": "rej.test@example.com",
        "farm_name": "Finca Rechazo",
        "farm_location": "X",
        "requested_role": "admin",
    }
    submit = await client.post("/api/v1/access-requests/", json=payload)
    assert submit.status_code == 200
    request_id = submit.json()["id"]

    sa_token = token_factory(super_admin_user)
    headers = {"Authorization": f"Bearer {sa_token}"}

    rej = await client.post(
        f"/api/v1/access-requests/{request_id}/reject",
        headers=headers,
        json={"notes": "Falta info"},
    )
    assert rej.status_code == 200
    assert rej.json()["status"] == "rejected"
    assert rej.json()["decision_notes"] == "Falta info"

    # Resubmit allowed because the previous one is no longer pending
    resub = await client.post("/api/v1/access-requests/", json=payload)
    assert resub.status_code == 200, resub.text
    assert resub.json()["id"] != request_id


async def test_magic_link_approve_invalid_token(app, client, super_admin_user: UUID, token_factory):
    submit = await client.post(
        "/api/v1/access-requests/",
        json={
            "full_name": "Magic",
            "email": "magic@example.com",
            "farm_name": "Finca Magic",
            "farm_location": "X",
            "requested_role": "admin",
        },
    )
    request_id = submit.json()["id"]
    resp = await client.get(f"/api/v1/access-requests/{request_id}/approve?token=not-a-real-token")
    assert resp.status_code == 403
    assert "Enlace inv" in resp.text


async def test_auth_profile_endpoint_works_without_tenant_header(
    app, client, super_admin_user: UUID, token_factory
):
    sa_token = token_factory(super_admin_user)
    resp = await client.get(
        "/api/v1/auth/profile",
        headers={"Authorization": f"Bearer {sa_token}"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["email"] == "superadmin@example.com"
    assert body["is_super_admin"] is True
