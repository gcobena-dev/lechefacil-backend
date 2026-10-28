from __future__ import annotations

import pytest


@pytest.fixture()
def headers(seeded_memberships, tenant_id, token_factory):
    return {
        "Authorization": f"Bearer {token_factory(seeded_memberships['admin'])}",
        "X-Tenant-ID": str(tenant_id),
    }


async def _animal(client, headers, tag: str, sex: str, name: str | None = None) -> str:
    response = await client.post(
        "/api/v1/animals/", json={"tag": tag, "name": name, "sex": sex}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def test_herd_bulls_can_be_imported_into_the_catalog(client, headers):
    bull = await _animal(client, headers, "T-1", "MALE", "Javier")
    unnamed = await _animal(client, headers, "T-2", "MALE")
    await _animal(client, headers, "V-1", "FEMALE")

    response = await client.get("/api/v1/reproduction/sires/herd-candidates", headers=headers)
    assert response.status_code == 200
    assert [c["tag"] for c in response.json()] == ["T-1", "T-2"]

    response = await client.post(
        "/api/v1/reproduction/sires/import-from-herd",
        json={"animal_ids": [bull, unnamed]},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    created = {s["animal_id"]: s for s in response.json()}
    assert created[bull]["name"] == "Javier"
    assert created[bull]["short_code"] == "T-1"
    assert created[unnamed]["name"] == "T-2"

    # Already in the catalog: no longer offered, and not importable twice
    response = await client.get("/api/v1/reproduction/sires/herd-candidates", headers=headers)
    assert response.json() == []
    response = await client.post(
        "/api/v1/reproduction/sires/import-from-herd",
        json={"animal_ids": [bull]},
        headers=headers,
    )
    assert response.status_code in (400, 422)


async def test_catalog_sire_can_only_link_a_herd_male(client, headers):
    cow = await _animal(client, headers, "V-2", "FEMALE")
    bull = await _animal(client, headers, "T-3", "MALE", "Toro")

    response = await client.post(
        "/api/v1/reproduction/sires",
        json={"name": "Vaca no", "animal_id": cow},
        headers=headers,
    )
    assert response.status_code in (400, 422)

    response = await client.post(
        "/api/v1/reproduction/sires", json={"name": "Toro", "animal_id": bull}, headers=headers
    )
    assert response.status_code == 201, response.text
    sire = response.json()

    # Editing the same entry keeps its own link
    response = await client.put(
        f"/api/v1/reproduction/sires/{sire['id']}",
        json={"name": "Toro de la finca", "animal_id": bull},
        headers=headers,
    )
    assert response.status_code == 200, response.text

    # A second entry cannot claim the same bull
    response = await client.post(
        "/api/v1/reproduction/sires", json={"name": "Otro", "animal_id": bull}, headers=headers
    )
    assert response.status_code in (400, 422)
