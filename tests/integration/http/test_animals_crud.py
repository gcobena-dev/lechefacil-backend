from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from src.infrastructure.db.orm.animal import AnimalORM


async def test_animals_crud_flow(app, client, seeded_memberships, tenant_id, token_factory):
    admin_token = token_factory(seeded_memberships["admin"])
    manager_token = token_factory(seeded_memberships["manager"])
    worker_token = token_factory(seeded_memberships["worker"])
    admin_headers = {
        "Authorization": f"Bearer {admin_token}",
        "X-Tenant-ID": str(tenant_id),
    }
    manager_headers = {
        "Authorization": f"Bearer {manager_token}",
        "X-Tenant-ID": str(tenant_id),
    }
    worker_headers = {
        "Authorization": f"Bearer {worker_token}",
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


async def test_update_returns_bumped_version_and_rejects_the_stale_one(
    client, seeded_memberships, tenant_id, token_factory
):
    """A second save with the version from the first one must be a 409.

    This is the contract the web client kept breaking: it held a cached copy of
    the animal, replayed its `version`, and got a conflict on an edit that had
    nothing to conflict with.
    """
    headers = {
        "Authorization": f"Bearer {token_factory(seeded_memberships['admin'])}",
        "X-Tenant-ID": str(tenant_id),
    }
    created = (
        await client.post(
            "/api/v1/animals/",
            json={"tag": "A-300", "name": "Sto Domingo #6", "status": "active"},
            headers=headers,
        )
    ).json()

    first = await client.put(
        f"/api/v1/animals/{created['id']}",
        json={"version": created["version"], "name": "Sto Domingo #6 bis"},
        headers=headers,
    )
    assert first.status_code == 200
    assert first.json()["version"] == created["version"] + 1

    stale = await client.put(
        f"/api/v1/animals/{created['id']}",
        json={"version": created["version"], "name": "otra vez"},
        headers=headers,
    )
    assert stale.status_code == 409

    fresh = await client.put(
        f"/api/v1/animals/{created['id']}",
        json={"version": first.json()["version"], "name": "otra vez"},
        headers=headers,
    )
    assert fresh.status_code == 200
    assert fresh.json()["name"] == "otra vez"


async def test_explicit_null_clears_a_field_and_omitting_it_does_not(
    client, seeded_memberships, tenant_id, token_factory
):
    headers = {
        "Authorization": f"Bearer {token_factory(seeded_memberships['admin'])}",
        "X-Tenant-ID": str(tenant_id),
    }
    created = (
        await client.post(
            "/api/v1/animals/",
            json={
                "tag": "A-400",
                "name": "Luna",
                "birth_date": "2020-01-01",
                "status": "active",
            },
            headers=headers,
        )
    ).json()
    assert created["birth_date"] == "2020-01-01"

    # Omitted field: untouched.
    omitted = await client.put(
        f"/api/v1/animals/{created['id']}",
        json={"version": created["version"], "name": "Luna II"},
        headers=headers,
    )
    assert omitted.status_code == 200
    assert omitted.json()["birth_date"] == "2020-01-01"

    # Explicit null: cleared.
    cleared = await client.put(
        f"/api/v1/animals/{created['id']}",
        json={"version": omitted.json()["version"], "birth_date": None},
        headers=headers,
    )
    assert cleared.status_code == 200
    assert cleared.json()["birth_date"] is None
    assert cleared.json()["name"] == "Luna II"


async def test_switching_to_an_external_sire_clears_the_internal_one(
    client, seeded_memberships, tenant_id, token_factory
):
    headers = {
        "Authorization": f"Bearer {token_factory(seeded_memberships['admin'])}",
        "X-Tenant-ID": str(tenant_id),
    }
    sire = (
        await client.post(
            "/api/v1/animals/",
            json={"tag": "S-1", "name": "Toro", "sex": "MALE", "status": "active"},
            headers=headers,
        )
    ).json()
    calf = (
        await client.post(
            "/api/v1/animals/",
            json={"tag": "C-1", "name": "Cría", "sex": "FEMALE", "status": "active"},
            headers=headers,
        )
    ).json()

    linked = await client.put(
        f"/api/v1/animals/{calf['id']}",
        json={"version": calf["version"], "sire_id": sire["id"]},
        headers=headers,
    )
    assert linked.status_code == 200
    assert linked.json()["sire_id"] == sire["id"]

    swapped = await client.put(
        f"/api/v1/animals/{calf['id']}",
        json={
            "version": linked.json()["version"],
            "sire_id": None,
            "external_sire_code": "EXT-99",
        },
        headers=headers,
    )
    assert swapped.status_code == 200
    assert swapped.json()["sire_id"] is None
    assert swapped.json()["external_sire_code"] == "EXT-99"
