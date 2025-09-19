from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from src.infrastructure.db.orm.animal import AnimalORM


async def test_animals_crud_flow(app, client, seeded_memberships, tenant_id):
    admin_headers = {
        "Authorization": f"Bearer {seeded_memberships['admin']}",
        "X-Tenant-ID": str(tenant_id),
    }
    manager_headers = {
        "Authorization": f"Bearer {seeded_memberships['manager']}",
        "X-Tenant-ID": str(tenant_id),
    }
    worker_headers = {
        "Authorization": f"Bearer {seeded_memberships['worker']}",
        "X-Tenant-ID": str(tenant_id),
    }

    payload = {
        "tag": "A-100",
        "name": "Bella",
        "breed": "Holstein",
        "status": "active",
    }
    create_response = await client.post("/api/v1/animals/", json=payload, headers=admin_headers)
    assert create_response.status_code == 201
    created = create_response.json()
    animal_id = created["id"]

    list_response = await client.get("/api/v1/animals/", headers=admin_headers)
    assert list_response.status_code == 200
    assert list_response.json()["items"][0]["id"] == animal_id

    update_payload = {
        "version": created["version"],
        "name": "Bella Prime",
        "status": "sold",
    }
    update_response = await client.put(
        f"/api/v1/animals/{animal_id}", json=update_payload, headers=manager_headers
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["name"] == "Bella Prime"
    assert updated["status"] == "sold"

    worker_update = await client.put(
        f"/api/v1/animals/{animal_id}",
        json={"version": updated["version"], "name": "Nope"},
        headers=worker_headers,
    )
    assert worker_update.status_code == 403

    manager_delete = await client.delete(f"/api/v1/animals/{animal_id}", headers=manager_headers)
    assert manager_delete.status_code == 403

    admin_delete = await client.delete(f"/api/v1/animals/{animal_id}", headers=admin_headers)
    assert admin_delete.status_code == 204

    async with app.state.session_factory() as session:  # type: ignore[attr-defined]
        animal_uuid = UUID(animal_id)
        result = await session.execute(select(AnimalORM).where(AnimalORM.id == animal_uuid))
        row = result.scalar_one()
        assert row.deleted_at is not None

    missing_response = await client.get(f"/api/v1/animals/{animal_id}", headers=admin_headers)
    assert missing_response.status_code == 404

    create_other = await client.post(
        "/api/v1/animals/",
        json={"tag": "A-200", "name": "Luna", "status": "active"},
        headers=admin_headers,
    )
    assert create_other.status_code == 201
    second = create_other.json()

    paginate = await client.get(
        "/api/v1/animals/",
        params={"limit": 1, "cursor": second["id"]},
        headers=admin_headers,
    )
    assert paginate.status_code == 200
    assert paginate.json()["items"] == []
