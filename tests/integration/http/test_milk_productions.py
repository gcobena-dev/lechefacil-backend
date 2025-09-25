from __future__ import annotations

from uuid import UUID


async def test_create_milk_production_for_animal(
    app, client, seeded_memberships, tenant_id: UUID, token_factory
):
    admin_token = token_factory(seeded_memberships["admin"])
    manager_token = token_factory(seeded_memberships["manager"])
    headers_admin = {
        "Authorization": f"Bearer {admin_token}",
        app.state.settings.tenant_header: str(tenant_id),
    }
    headers_manager = {
        "Authorization": f"Bearer {manager_token}",
        app.state.settings.tenant_header: str(tenant_id),
    }

    # Create an animal (admin)
    create_animal_payload = {
        "tag": "T-PRD-001",
        "name": "Vaca Prod 001",
        "breed": "Holstein",
        "birth_date": "2023-01-01",
        "lot": "L1",
        "status": "active",
    }
    resp = await client.post("/api/v1/animals/", json=create_animal_payload, headers=headers_admin)
    assert resp.status_code == 201
    animal_id = resp.json()["id"]

    # Create a milk production (manager)
    # Use kg with default density (1.03) -> 10 / 1.03 = 9.7087... -> 9.709 liters
    payload = {
        "date_time": "2025-01-01T06:00:00Z",
        "animal_id": animal_id,
        "input_unit": "kg",
        "input_quantity": 10,
        # density omitted -> will use tenant default
        "notes": "Ordeño matutino",
    }
    resp2 = await client.post("/api/v1/milk-productions/", json=payload, headers=headers_manager)
    assert resp2.status_code == 201, resp2.text
    body = resp2.json()
    assert body["animal_id"] == animal_id
    assert body["input_unit"] == "kg"
    assert body["input_quantity"] == "10"
    assert body["density"] == "1.03"
    assert body["volume_l"] == "9.709"

    # List by animal should include the record
    list_resp = await client.get(
        f"/api/v1/milk-productions/?animal_id={animal_id}", headers=headers_manager
    )
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert any(it["id"] == body["id"] for it in items)
